'use client';

import { ChatMessage } from '@/components/features/chat/ChatMessage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Message } from '@/types/chat';
import { Rocket, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { getTask } from '@/actions/tasks';

export default function ChatPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskid as string;
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current && shouldAutoScroll) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isNearBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 100;
      setShouldAutoScroll(isNearBottom);
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
      setMessages([
        { role: 'user', content: res.data.prompt },
        ...res.data.steps.map(step => ({ role: 'assistant' as const, type: step.type as Message['type'], content: step.result })),
      ]);
      if (shouldAutoScroll) {
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
    <div className="flex flex-col h-screen bg-gray-100">
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto p-4 pb-20 space-y-4"
        style={{
          scrollBehavior: 'smooth',
          overscrollBehavior: 'contain',
        }}
        onScroll={handleScroll}
      >
        <ChatMessage messages={messages} />
      </div>

      <div className="absolute bottom-0 left-0 right-0 p-4 pointer-events-none">
        <form className="w-full max-w-2xl mx-auto pointer-events-auto flex gap-4 items-center">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                className="rounded-full cursor-pointer"
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
          <div className="w-full relative flex bg-white rounded-2xl shadow-[0_0_15px_rgba(0,0,0,0.1)]">
            <Input
              value={isThinking ? 'Thinking...' : 'Task completed!'}
              aria-disabled={isThinking}
              onChange={() => {}}
              placeholder="Let's Imagine the Impossible, Create the Future Together"
              className="flex-1 pointer-events-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0 bg-transparent h-12 px-4"
              disabled={isThinking}
            />
            <Button
              type="button"
              disabled={isThinking}
              size="icon"
              variant="ghost"
              className="absolute cursor-pointer right-1 top-1/2 -translate-y-1/2 h-10 w-10 hover:bg-gray-100 rounded-xl"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
