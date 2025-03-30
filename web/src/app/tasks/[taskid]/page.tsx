'use client';

import { ChatMessages } from '@/components/features/chat/chat-messages';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Message } from '@/types/chat';
import { Rocket, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { getTask } from '@/actions/tasks';
import { Tasks } from '@prisma/client';
import { ChatPreview } from '@/components/features/chat/preview';
import { useCurrentMessageIndex } from '../hooks';

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskid as string;

  const [task, setTask] = useState<Tasks | null>(null);
  const [isNearBottom, setIsNearBottom] = useState(false);
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
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

  useEffect(() => {
    if (!taskId) return;
    let fetching = false;

    const fetchTask = async () => {
      if (fetching) return;
      fetching = true;
      const res = await getTask({ taskId });
      if (res.error || !res.data) {
        console.error('Error fetching task:', res.error);
        fetching = false;
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
      if (res.data!.status === 'failed' || res.data!.status === 'completed') {
        setIsThinking(false);
        clearInterval(interval);
      } else {
        setIsThinking(true);
      }
      fetching = false;
    };
    fetchTask();
    const interval = setInterval(fetchTask, 2000);
    return () => {
      clearInterval(interval);
    };
  }, [taskId, shouldAutoScroll]);

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

  return (
    <div className="relative flex h-screen bg-gray-100">
      <div className="relative flex h-screen flex-1 flex-col">
        <div
          ref={messagesContainerRef}
          className="flex-3/5 space-y-4 overflow-y-auto p-4 pb-20"
          style={{
            scrollBehavior: 'smooth',
            overscrollBehavior: 'contain',
          }}
          onScroll={handleScroll}
        >
          <ChatMessages messages={messages} />
        </div>
        <div className="pointer-events-none absolute right-0 bottom-0 left-0 p-4">
          <form className="pointer-events-auto mx-auto flex w-full max-w-2xl items-center gap-4">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  className="cursor-pointer rounded-full"
                  size="icon"
                  type="button"
                  onClick={() => {
                    router.push('/tasks');
                  }}
                >
                  <Rocket className="h-5 w-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>New Task</p>
              </TooltipContent>
            </Tooltip>
            <div className="relative flex w-full rounded-2xl bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)]">
              <Input
                value={isThinking ? 'Thinking...' : 'Task completed!'}
                aria-disabled={isThinking}
                onChange={() => {}}
                placeholder="Let's Imagine the Impossible, Create the Future Together"
                className="pointer-events-none h-12 flex-1 border-0 bg-transparent px-4 focus-visible:ring-0 focus-visible:ring-offset-0"
                disabled={isThinking}
              />
              <Button
                type="button"
                disabled={isThinking}
                size="icon"
                variant="ghost"
                className="absolute top-1/2 right-1 h-10 w-10 -translate-y-1/2 cursor-pointer rounded-xl hover:bg-gray-100"
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </form>
        </div>
      </div>
      <div className="flex min-w-[800px] flex-1 items-center justify-center p-2">
        <ChatPreview message={messages[currentMessageIndex]} />
      </div>
    </div>
  );
}
