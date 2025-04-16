'use client';

import { getTask, restartTask, terminateTask } from '@/actions/tasks';
import { ChatInput } from '@/components/features/chat/input';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { usePreviewData } from '@/components/features/chat/preview/store';
import { aggregateMessages } from '@/lib/chat-messages';
import { Message } from '@/lib/chat-messages/types';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskid as string;

  const { setData: setPreviewData } = usePreviewData();

  const [isNearBottom, setIsNearBottom] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const shouldAutoScroll = isNearBottom;

  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isNearBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
      setIsNearBottom(isNearBottom);
    }
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current && shouldAutoScroll) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  const refreshTask = async () => {
    const res = await getTask({ taskId });
    if (res.error || !res.data) {
      console.error('Error fetching task:', res.error);
      return;
    }
    setMessages(res.data.progresses.map(step => ({ ...step, index: step.index! || 0, type: step.type as any, role: 'assistant' as const })));
    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
      const nextMessage = messages[messages.length - 1];
      if (shouldAutoScroll) {
        if (nextMessage?.type === 'agent:lifecycle:step:think:browser:browse:complete') {
          setPreviewData({
            type: 'browser',
            url: nextMessage.content.url,
            title: nextMessage.content.title,
            screenshot: nextMessage.content.screenshot,
          });
        }
        if (nextMessage?.type === 'agent:lifecycle:step:act:tool:execute:start') {
          setPreviewData({ type: 'tool', toolId: nextMessage.content.id });
        }
      }
    }
    setIsThinking(res.data!.status !== 'completed' && res.data!.status !== 'failed' && res.data!.status !== 'terminated');
    setIsTerminating(res.data!.status === 'terminating');
  };

  useEffect(() => {
    setPreviewData(null);
    if (!taskId) return;
    refreshTask();
  }, [taskId]);

  useEffect(() => {
    refreshTask();
    if (!taskId || !isThinking) return;
    const interval = setInterval(refreshTask, 2000);
    return () => {
      clearInterval(interval);
    };
  }, [taskId, isThinking, shouldAutoScroll]);

  useEffect(() => {
    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
    }
  }, [messages, shouldAutoScroll]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSubmit = async (value: { prompt: string; tools: string[]; files: File[] }) => {
    try {
      const res = await restartTask({ taskId, prompt: value.prompt, tools: value.tools, files: value.files });
      if (res.error) {
        console.error('Error restarting task:', res.error);
      }
      setIsThinking(true);
      router.refresh();
    } catch (error) {
      console.error('Error submitting task:', error);
    }
  };

  return (
    <div className="flex h-screen w-full flex-row justify-between">
      <div className="flex-1">
        <div className="relative flex h-screen flex-col">
          <div
            ref={messagesContainerRef}
            className="flex-3/5 space-y-4 overflow-y-auto p-4 pb-60"
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
            onTerminate={async () => {
              await terminateTask({ taskId });
              router.refresh();
            }}
            taskId={taskId}
          />
        </div>
      </div>
      <div className="min-w-[800px] flex-1 items-center justify-center p-2">
        <ChatPreview taskId={taskId} messages={messages} />
      </div>
    </div>
  );
}
