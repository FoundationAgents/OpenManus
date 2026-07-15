import { ChatInput } from '@/components/features/chat/input';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { usePreviewData } from '@/components/features/chat/preview/store';
import { useAutoScroll } from '@/hooks/use-auto-scroll';
import { useConversations } from '@/hooks/use-conversations';
import { aggregateMessages } from '@/libs/chat-messages';
import type { Message } from '@/libs/chat-messages/types';
import {
  getConversationHistory,
  getConversationHistoryAll,
  getIntegrationsHealth,
  sendConversationMessage,
  type IntegrationsHealth,
} from '@/services/conversations';
import { createTask, getTask, getTaskEvents, sendTaskMessage, terminateTask } from '@/services/tasks';
import { GaugeIcon, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';

export default function TaskDetailPage({ selectedModel }: { selectedModel?: string }) {
  const params = useParams();
  const routeTaskId = params.taskId as string | undefined;
  const routeConversationId = params.conversationId as string | undefined;
  const navigate = useNavigate();

  const { data: previewData, setData: setPreviewData } = usePreviewData();
  const { refreshConversations, setActiveConversationId } = useConversations();

  const [messages, setMessages] = useState<Message[]>([]);
  const [historyWindow, setHistoryWindow] = useState(80);
  const [activeTaskId, setActiveTaskId] = useState<string | undefined>(routeTaskId);
  const [isThinking, setIsThinking] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const [isTaskCompleted, setIsTaskCompleted] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [integrationsHealth, setIntegrationsHealth] = useState<IntegrationsHealth | null>(null);
  const [isPreviewCollapsed, setIsPreviewCollapsed] = useState(false);
  const [performanceMode, setPerformanceMode] = useState(
    () => localStorage.getItem('openmanus.performanceMode') === '1',
  );
  // Step progress and token tracking (driven by agent events)
  const [stepProgress, setStepProgress] = useState<{ current: number; max: number } | null>(null);
  const [totalTokens, setTotalTokens] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const currentStreamTaskIdRef = useRef<string | null>(null);
  const eventErrorCountRef = useRef(0);
  const isTaskCompletedRef = useRef(false);
  const shouldAutoScrollRef = useRef(false);
  const seenEventKeysRef = useRef<Set<string>>(new Set());

  const { containerRef: messagesContainerRef, shouldAutoScroll, handleScroll, scrollToBottom } = useAutoScroll();
  const visibleMessages = useMemo(() => {
    if (historyWindow >= messages.length) return messages;
    return messages.slice(messages.length - historyWindow);
  }, [historyWindow, messages]);
  const aggregatedMessages = useMemo(() => aggregateMessages(visibleMessages), [visibleMessages]);
  const lastFinishedAt = useMemo(() => {
    const last = [...messages]
      .reverse()
      .find(m => m.type === 'agent:lifecycle:complete' || m.type === 'agent:lifecycle:terminated');
    return last?.createdAt || null;
  }, [messages]);

  useEffect(() => {
    shouldAutoScrollRef.current = shouldAutoScroll;
  }, [shouldAutoScroll]);

  const toMessage = useCallback((data: any): Message => {
    const key = data.id || `${data.task_id || ''}:${data.name}:${JSON.stringify(data.content || {})}`;
    return {
      ...data,
      index: key,
      createdAt: data.created_at ? new Date(data.created_at) : undefined,
      type: data.name as Message['type'],
      role: 'assistant' as const,
    };
  }, []);

  const applyPreviewFromMessage = useCallback((newMessage: Message) => {
    if (newMessage.type === 'agent:lifecycle:step:think:browser:browse:complete') {
      setPreviewData({
        type: 'browser',
        url: newMessage.content.url,
        title: newMessage.content.title,
        screenshot: newMessage.content.screenshot,
      });
    }
    if (newMessage.type === 'agent:lifecycle:step:act:tool:execute:start') {
      setPreviewData({ type: 'tool', toolId: newMessage.content.id });
    }
    if (newMessage.type === 'agent:lifecycle:step:act:tool:file:updated') {
      const path = String(newMessage.content.path || '').replace(/^\/app\/workspace\/?/, '');
      setPreviewData({ type: 'workspace', path });
    }
  }, [setPreviewData]);

  const appendLocalUserMessage = useCallback((prompt: string) => {
    const key = `local:user:${Date.now()}:${Math.random().toString(36).slice(2)}`;
    seenEventKeysRef.current.add(key);
    setMessages(prevMessages => [
      ...prevMessages,
      {
        index: key,
        role: 'user',
        content: prompt,
        createdAt: new Date(),
      },
    ]);
  }, []);

  const setupEventSource = useCallback((taskId?: string) => {
    if (!taskId) return;
    currentStreamTaskIdRef.current = taskId;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (reconnectTimerRef.current) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const eventSource = getTaskEvents({ taskId });
    eventSourceRef.current = eventSource;
    eventErrorCountRef.current = 0;

    eventSource.onmessage = event => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          const key = data.id || `${taskId}:${data.name}:${JSON.stringify(data.content || {})}`;
          if (seenEventKeysRef.current.has(key)) return;
          seenEventKeysRef.current.add(key);
          const newMessage = toMessage({ ...data, id: key, task_id: taskId });

          // --- Step progress ---
          if (data.name === 'agent:lifecycle:step:start') {
            const step = Number(data.content?.step ?? 0);
            const max = Number(data.content?.max_steps ?? 0);
            if (step > 0) setStepProgress({ current: step, max });
          } else if (data.name === 'agent:lifecycle:complete' || data.name === 'agent:lifecycle:terminated') {
            setStepProgress(null);
          }

          // --- Token counter ---
          if (data.name === 'agent:lifecycle:token_count') {
            const total = Number((data.content?.total_input ?? 0)) + Number((data.content?.total_completion ?? 0));
            if (total > 0) setTotalTokens(total);
          }

          setMessages(prevMessages => {
            const request = String(newMessage.content?.request || '').trim();
            const baseMessages =
              newMessage.type === 'agent:lifecycle:start' && request
                ? prevMessages.filter(
                    message =>
                      !(
                        !message.type &&
                        message.role === 'user' &&
                        String(message.content || '').trim() === request
                      ),
                  )
                : prevMessages;
            const updatedMessages = [...baseMessages, newMessage];

            if (shouldAutoScrollRef.current) {
              applyPreviewFromMessage(newMessage);
            }

            return updatedMessages;
          });

          if (data.name === 'agent:lifecycle:complete') {
            setIsThinking(false);
            setIsTerminating(false);
            setIsTaskCompleted(true);
            isTaskCompletedRef.current = true;
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            if (reconnectTimerRef.current) {
              window.clearTimeout(reconnectTimerRef.current);
              reconnectTimerRef.current = null;
            }
          } else if (data.name === 'agent:lifecycle:terminated') {
            setIsThinking(false);
            setIsTerminating(false);
            setIsTaskCompleted(true);
            isTaskCompletedRef.current = true;
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
            if (reconnectTimerRef.current) {
              window.clearTimeout(reconnectTimerRef.current);
              reconnectTimerRef.current = null;
            }
          } else if (data.name === 'agent:lifecycle:terminating') {
            setIsTerminating(true);
          } else {
            setIsThinking(prev => prev || true);
          }
        }
      } catch (error) {
        console.error('Error parsing event data:', error);
      }
    };

    eventSource.onerror = error => {
      console.error('EventSource error:', error);
      console.error('EventSource readyState:', eventSource.readyState);
      console.error('EventSource URL:', eventSource.url);

      if (isTaskCompletedRef.current) {
        console.log('Task completed, ignoring connection error');
        return;
      }

      eventErrorCountRef.current += 1;
      let errorMessage = 'Connection error';

      if (eventSource.readyState === EventSource.CONNECTING) {
        console.error('Connection failed - trying to reconnect...');
        // Browser auto-reconnect is expected transient behavior for SSE.
        // Avoid noisy toasts unless retries persist.
        if (eventErrorCountRef.current >= 8) {
          errorMessage = 'Connection unstable, retrying...';
          toast.error(errorMessage);
        }
        return;
      } else if (eventSource.readyState === EventSource.CLOSED) {
        console.error('Connection closed');
        // Closed streams can happen on proxy/container restarts.
        // Recreate the EventSource manually if task isn't terminal yet.
        if (!reconnectTimerRef.current && currentStreamTaskIdRef.current) {
          const delay = Math.min(12000, 1000 * Math.max(1, eventErrorCountRef.current));
          reconnectTimerRef.current = window.setTimeout(() => {
            reconnectTimerRef.current = null;
            if (isTaskCompletedRef.current) return;
            setupEventSource(currentStreamTaskIdRef.current || undefined);
          }, delay);
        }
        if (eventErrorCountRef.current >= 3) {
          errorMessage = 'Connection unstable, retrying...';
          toast.error(errorMessage);
        }
        return;
      }

      toast.error(errorMessage);

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    eventSource.onopen = () => {
      console.log('EventSource connected');
      if (isTaskCompletedRef.current) {
        return;
      }
      setIsThinking(true);
    };
  }, [applyPreviewFromMessage, toMessage]);

  const loadConversation = useCallback(async (targetConversationId: string) => {
    try {
      let history = await getConversationHistoryAll(targetConversationId);
      // Defensive fallback for legacy/misaligned event windows:
      // retry with a larger page before replacing the chat with empty content.
      if ((!history.events || history.events.length === 0) && (history.tasks || []).length > 0) {
        history = await getConversationHistory(targetConversationId, 1200);
      }
      seenEventKeysRef.current = new Set();
      const nextMessages = history.events.map(event => {
        const key = event.id || `${event.task_id || ''}:${event.name}:${JSON.stringify(event.content || {})}`;
        seenEventKeysRef.current.add(key);
        return toMessage({ ...event, id: key });
      });
      if (nextMessages.length === 0 && messages.length > 0) {
        // Keep current UI state instead of wiping chat on an empty history payload.
        setConversationId(targetConversationId);
        setActiveConversationId(targetConversationId);
        return;
      }
      const latestTask = [...history.tasks].reverse().find(Boolean);
      const activeTask = [...history.tasks].reverse().find(task => !['COMPLETED', 'FAILED', 'INTERRUPTED'].includes(String(task.status || '')));
      setMessages(nextMessages);
      setHistoryWindow(80);
      setConversationId(targetConversationId);
      setActiveTaskId(activeTask?.task_id || latestTask?.task_id);
      setActiveConversationId(targetConversationId);
      setIsTaskCompleted(!activeTask && Boolean(latestTask));
      isTaskCompletedRef.current = !activeTask && Boolean(latestTask);
      setIsThinking(Boolean(activeTask));
      setIsTerminating(false);
      if (nextMessages.length) {
        const lastPreviewMessage = [...nextMessages].reverse().find(message =>
          message.type === 'agent:lifecycle:step:think:browser:browse:complete' ||
          message.type === 'agent:lifecycle:step:act:tool:execute:start' ||
          message.type === 'agent:lifecycle:step:act:tool:file:updated'
        );
        if (lastPreviewMessage) applyPreviewFromMessage(lastPreviewMessage);
      }
      if (activeTask?.task_id) {
        setupEventSource(activeTask.task_id);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not load conversation history');
      // Keep current in-memory messages instead of wiping the chat on transient backend errors.
      setConversationId(targetConversationId);
      setActiveConversationId(targetConversationId);
    }
  }, [applyPreviewFromMessage, setActiveConversationId, setupEventSource, toMessage]);

  useEffect(() => {
    let cancelled = false;

    // Do not clear the UI before remote history loads successfully.
    // This prevents "empty chat" when backend restarts or transient network errors happen.
    setIsThinking(false);
    setIsTerminating(false);
    if (!routeTaskId && !routeConversationId) return;

    const initializeTask = async () => {
      if (routeConversationId) {
        await loadConversation(routeConversationId);
        return;
      }

      const task = await getTask({ taskId: routeTaskId! });
      if (cancelled) return;

      const status = task.data?.status;
      if (task.data?.conversation_id) {
        navigate(`/conversations/${task.data.conversation_id}`, { replace: true });
        return;
      }

      setActiveTaskId(routeTaskId);
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'INTERRUPTED') {
        setIsTaskCompleted(true);
        isTaskCompletedRef.current = true;
      } else {
        setupEventSource(routeTaskId);
      }
    };

    initializeTask();

    return () => {
      cancelled = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [loadConversation, navigate, routeConversationId, routeTaskId, setPreviewData, setupEventSource]);

  useEffect(() => {
    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
    }
  }, [messages, shouldAutoScroll, scrollToBottom]);

  useEffect(() => {
    // On first open, jump to latest messages.
    requestAnimationFrame(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
    });
  }, [conversationId, messagesContainerRef]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!conversationId) {
      setIntegrationsHealth(null);
      return;
    }
    let stopped = false;
    const loadHealth = async () => {
      try {
        const data = await getIntegrationsHealth(conversationId);
        if (!stopped) setIntegrationsHealth(data);
      } catch {
        if (!stopped) setIntegrationsHealth(null);
      }
    };
    loadHealth();
    const timer = window.setInterval(() => {
      if (!document.hidden) loadHealth();
    }, performanceMode ? 60000 : 30000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [conversationId, performanceMode]);

  const handleSubmit = async (value: { prompt: string }) => {
    const prompt = value.prompt.trim();
    if (!prompt) return;
    appendLocalUserMessage(prompt);
    setIsThinking(true);
    setIsTaskCompleted(false);
    isTaskCompletedRef.current = false;
    try {
      if (isThinking && !isTaskCompleted && activeTaskId) {
        const res = await sendTaskMessage({ taskId: activeTaskId, message: prompt });
        if (res.error) {
          toast.error(res.error);
          setIsThinking(false);
        }
        return;
      }

      if (conversationId) {
        const sent = await sendConversationMessage(conversationId, prompt, selectedModel);
        await refreshConversations();
        if (sent.task_id) {
          setActiveTaskId(sent.task_id);
          setupEventSource(sent.task_id);
        }
        if (sent.created_task) {
          setIsThinking(true);
        }
        return;
      }

      const res = await createTask({
        prompt,
        conversationId,
        model: selectedModel,
      });
      if (res.status === 409 && activeTaskId) {
        const inboxRes = await sendTaskMessage({ taskId: activeTaskId, message: prompt });
        if (inboxRes.error) {
          toast.error(inboxRes.error);
          setIsThinking(false);
          return;
        }
        toast.success('Sent to running task');
        return;
      }
      if (res.error || !res.data?.task_id) {
        console.error('Error restarting task:', res.error);
        toast.error(res.error || 'Could not start follow-up task');
        setIsThinking(false);
        return;
      }
      await refreshConversations();
      setIsThinking(true);
      setActiveTaskId(res.data.task_id);
      if (res.data.conversation_id && res.data.conversation_id !== conversationId) {
        navigate(`/conversations/${res.data.conversation_id}`, { replace: true });
      } else if (conversationId) {
        await loadConversation(conversationId);
      }
    } catch (error) {
      console.error('Error submitting task:', error);
      toast.error(error instanceof Error ? error.message : 'Could not send message');
      setIsThinking(false);
    }
  };

  const handleTerminate = async () => {
    try {
      if (!activeTaskId) return;
      const res = await terminateTask({ taskId: activeTaskId });
      if (res.error) {
        console.error('Error terminating task:', res.error);
      }
      if (conversationId) await loadConversation(conversationId);
    } catch (error) {
      console.error('Error terminating task:', error);
    }
  };

  return (
    <div className="flex h-full w-full flex-row justify-between">
      <div className="flex min-w-0 flex-1 flex-col border-r bg-background">
        <div className="flex h-12 items-center gap-2 border-b px-5">
          <div className="font-semibold">OpenManus</div>
          {isThinking ? (
            <div className="text-xs text-muted-foreground">Working</div>
          ) : lastFinishedAt ? (
            <div className="text-xs text-muted-foreground">
              Idle · last completed {lastFinishedAt.toLocaleTimeString()}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">Idle</div>
          )}
          {/* Step progress pill */}
          {stepProgress && stepProgress.current > 0 && (
            <div className="flex items-center gap-1.5 rounded-full border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
              <div
                className="h-1.5 rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, (stepProgress.current / Math.max(stepProgress.max, 1)) * 100)}%`, minWidth: '6px', maxWidth: '60px' }}
              />
              <span>Step {stepProgress.current}{stepProgress.max > 0 ? ` / ${stepProgress.max}` : ''}</span>
            </div>
          )}
          {/* Token counter */}
          {totalTokens > 0 && (
            <div className="text-[11px] text-muted-foreground tabular-nums" title="Total tokens used in this session">
              ⚡ {totalTokens.toLocaleString()} tok
            </div>
          )}
          <div className="ml-auto flex items-center gap-2">
            <button
              className="inline-flex h-7 items-center gap-1 rounded border px-2 text-[11px] hover:bg-muted"
              onClick={() => {
                setIsPreviewCollapsed(false);
                setPreviewData({ type: 'live' });
              }}
              title="Open live monitor"
              aria-label="Open live monitor"
            >
              Live
            </button>
            <button
              className="inline-flex h-7 w-7 items-center justify-center rounded border hover:bg-muted"
              onClick={() => setIsPreviewCollapsed(current => !current)}
              title={isPreviewCollapsed ? 'Show Manus computer panel' : 'Hide Manus computer panel'}
              aria-label={isPreviewCollapsed ? 'Show Manus computer panel' : 'Hide Manus computer panel'}
            >
              {isPreviewCollapsed ? <PanelLeftOpen className="size-4" /> : <PanelLeftClose className="size-4" />}
            </button>
            <button
              className={`inline-flex h-7 items-center gap-1 rounded border px-2 text-[11px] hover:bg-muted ${performanceMode ? 'border-emerald-500/40 text-emerald-600' : ''}`}
              onClick={() => {
                setPerformanceMode(prev => {
                  const next = !prev;
                  localStorage.setItem('openmanus.performanceMode', next ? '1' : '0');
                  return next;
                });
              }}
              title={performanceMode ? 'Performance mode enabled' : 'Enable performance mode'}
              aria-label="Toggle performance mode"
            >
              <GaugeIcon className="size-3.5" />
              {performanceMode ? 'Perf On' : 'Perf Off'}
            </button>
          </div>
        </div>
        <div className="relative flex h-full flex-col">
          <div
            ref={messagesContainerRef}
            className="h-full space-y-4 overflow-y-auto p-4 pb-60"
            style={{
              scrollBehavior: 'smooth',
              overscrollBehavior: 'contain',
            }}
            onScroll={() => {
              handleScroll();
              const el = messagesContainerRef.current;
              if (!el) return;
              // Lazy-reveal older history only when the user intentionally scrolls up.
              if (el.scrollTop < 120 && historyWindow < messages.length) {
                const prevHeight = el.scrollHeight;
                setHistoryWindow(windowSize => Math.min(messages.length, windowSize + 80));
                requestAnimationFrame(() => {
                  const target = messagesContainerRef.current;
                  if (!target) return;
                  const diff = target.scrollHeight - prevHeight;
                  target.scrollTop = target.scrollTop + diff;
                });
              }
            }}
          >
            <ChatMessages messages={aggregatedMessages} />
          </div>
          <ChatInput
            status={isTerminating ? 'terminating' : isThinking ? 'thinking' : isTaskCompleted ? 'completed' : 'idle'}
            onSubmit={handleSubmit}
            onTerminate={handleTerminate}
            taskId={activeTaskId}
          />
        </div>
      </div>
      {!isPreviewCollapsed && (
        <div className="hidden w-[44vw] min-w-[420px] max-w-[760px] items-center justify-center bg-muted/30 p-2 lg:flex">
          <ChatPreview
            taskId={activeTaskId || conversationId || 'workspace'}
            conversationId={conversationId}
            messages={messages}
            integrationsHealth={integrationsHealth}
            performanceMode={performanceMode}
            pollRuntime={isThinking || previewData?.type === 'runtime'}
          />
        </div>
      )}
    </div>
  );
}
