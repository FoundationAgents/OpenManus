import { ChatInput } from '@/components/features/chat/input';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { usePreviewData } from '@/components/features/chat/preview/store';
import { useAutoScroll } from '@/hooks/use-auto-scroll';
import { aggregateMessages } from '@/libs/chat-messages';
import type { Message } from '@/libs/chat-messages/types';
import { createTask, getTaskEvents, terminateTask } from '@/services/tasks';
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';

export default function TaskDetailPage() {
  const params = useParams();
  const taskId = params.taskId as string;

  const { setData: setPreviewData } = usePreviewData();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const [isTaskCompleted, setIsTaskCompleted] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  const { containerRef: messagesContainerRef, shouldAutoScroll, handleScroll, scrollToBottom } = useAutoScroll();

  const setupEventSource = () => {
    if (!taskId || isTaskCompleted) return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = getTaskEvents({ taskId });
    eventSourceRef.current = eventSource;

    eventSource.onmessage = event => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'progress') {
          const newMessage: Message = {
            ...data,
            index: data.index || 0,
            type: data.name as any,
            role: 'assistant' as const,
          };

          setMessages(prevMessages => {
            const updatedMessages = [...prevMessages, newMessage];

            if (shouldAutoScroll) {
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
            }

            return updatedMessages;
          });

          if (data.name === 'agent:lifecycle:complete') {
            setIsThinking(false);
            setIsTerminating(false);
            setIsTaskCompleted(true);
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
          } else if (data.name === 'agent:lifecycle:terminated') {
            setIsThinking(false);
            setIsTerminating(false);
            setIsTaskCompleted(true);
            if (eventSourceRef.current) {
              eventSourceRef.current.close();
              eventSourceRef.current = null;
            }
          } else if (data.name === 'agent:lifecycle:terminating') {
            setIsTerminating(true);
          } else {
            setIsThinking(true);
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

      if (isTaskCompleted) {
        console.log('Task completed, ignoring connection error');
        return;
      }

      let errorMessage = 'Connection error';

      if (eventSource.readyState === EventSource.CONNECTING) {
        console.error('Connection failed - trying to reconnect...');
        errorMessage = 'Connection failed, trying to reconnect...';
      } else if (eventSource.readyState === EventSource.CLOSED) {
        console.error('Connection closed');
        errorMessage = 'Connection closed';
      }

      toast.error(errorMessage);
      setIsThinking(false);

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    eventSource.onopen = () => {
      console.log('EventSource connected');
      setIsThinking(true);
    };
  };

  useEffect(() => {
    setPreviewData(null);
    setIsTaskCompleted(false);
    if (!taskId) return;
    setupEventSource();
  }, [taskId]);

  useEffect(() => {
    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
    }
  }, [messages, shouldAutoScroll, scrollToBottom]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSubmit = async (value: { prompt: string }) => {
    try {
      const res = await createTask({ taskId, prompt: value.prompt });
      if (res.error) {
        console.error('Error restarting task:', res.error);
      }
      setIsThinking(true);
      window.location.reload();
    } catch (error) {
      console.error('Error submitting task:', error);
    }
  };

  const handleTerminate = async () => {
    try {
      const res = await terminateTask({ taskId });
      if (res.error) {
        console.error('Error terminating task:', res.error);
      }
      window.location.reload();
    } catch (error) {
      console.error('Error terminating task:', error);
    }
  };

  return (
    <div className="flex h-full w-full flex-row justify-between">
      <div className="flex-1/2 py-2">
        <div className="relative flex h-full flex-col">
          <div
            ref={messagesContainerRef}
            className="h-full space-y-4 overflow-y-auto p-4 pb-60"
            style={{
              scrollBehavior: 'smooth',
              overscrollBehavior: 'contain',
            }}
            onScroll={handleScroll}
          >
            <ChatMessages messages={aggregateMessages(messages)} />
          </div>
          <ChatInput
            status={isThinking ? 'thinking' : isTerminating ? 'terminating' : 'completed'}
            onSubmit={handleSubmit}
            onTerminate={handleTerminate}
            taskId={taskId}
          />
        </div>
      </div>
      <div className="max-w-[50vw] min-w-[400px] flex-1/2 items-center justify-center p-2">
        <ChatPreview taskId={taskId} messages={messages} />
      </div>
    </div>
  );
}
