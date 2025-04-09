'use client';

import { getTask, restartTask, terminateTask } from '@/actions/tasks';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { Message } from '@/types/chat';
import { Tasks } from '@prisma/client';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useCurrentMessageIndex } from '../hooks';
import { ChatInput } from '@/components/features/chat/input';

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskid as string;

  const [value, setValue] = useState('');
  const [task, setTask] = useState<Tasks | null>(null);
  const [isNearBottom, setIsNearBottom] = useState(false);
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const shouldAutoScroll = isNearBottom && currentMessageIndex === messages.length - 1;

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
    setTask(res.data);
    setMessages([
      { role: 'user', content: { prompt: res.data.prompt } },
      ...res.data.progresses.map(step => ({ role: 'assistant' as const, type: step.type as Message['type'], content: step.content as object })),
    ]);
    if (shouldAutoScroll) {
      setCurrentMessageIndex(messages.length - 1);
      requestAnimationFrame(scrollToBottom);
    }
    setIsThinking(res.data!.status !== 'completed' && res.data!.status !== 'failed' && res.data!.status !== 'terminated');
    setIsTerminating(res.data!.status === 'terminating');
  };

  useEffect(() => {
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
      setValue('');
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
            <ChatMessages messages={messages} />
          </div>
          <ChatInput
            status={isThinking ? 'thinking' : isTerminating ? 'terminating' : 'completed'}
            onSubmit={handleSubmit}
            onTerminate={async () => {
              await terminateTask({ taskId });
              router.refresh();
            }}
          />
        </div>
      </div>
      <div className="min-w-[800px] flex-1 items-center justify-center p-2">
        <ChatPreview message={messages[currentMessageIndex]} />
      </div>
    </div>
  );
}
