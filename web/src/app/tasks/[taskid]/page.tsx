'use client';

import { getTask, restartTask, terminateTask } from '@/actions/tasks';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Message } from '@/types/chat';
import { Tasks } from '@prisma/client';
import { PauseCircle, Rocket, Send } from 'lucide-react';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { useCurrentMessageIndex } from '../hooks';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

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

  const [openDialogConfirmTerminate, setOpenDialogConfirmTerminate] = useState(false);

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

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!value.trim()) return;

    try {
      const res = await restartTask({ taskId, prompt: value });
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isThinking || isTerminating) {
        return;
      }
      if (value.trim()) {
        handleSubmit(e as unknown as React.FormEvent<HTMLFormElement>);
      }
    }
  };

  return (
    <div className="flex h-screen w-full flex-row justify-between">
      <div className="flex-1">
        <div className="relative flex h-screen flex-col">
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
            <div className="pointer-events-auto mx-auto flex w-full max-w-2xl items-center gap-4">
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
                  value={value}
                  onChange={e => setValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isThinking || isTerminating}
                  placeholder={isTerminating ? 'Terminating...' : isThinking ? 'Thinking...' : 'Task completed!'}
                  className="h-12 flex-1 border-0 bg-transparent px-4 focus-visible:ring-0 focus-visible:ring-offset-0"
                />
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="absolute top-1/2 right-1 h-10 w-10 -translate-y-1/2 cursor-pointer rounded-xl hover:bg-gray-100"
                  onClick={e => {
                    if (isThinking || isTerminating) {
                      setOpenDialogConfirmTerminate(true);
                      refreshTask();
                    } else if (value.trim()) {
                      handleSubmit(e as unknown as React.FormEvent<HTMLFormElement>);
                    }
                  }}
                >
                  {isThinking || isTerminating ? <PauseCircle className="h-5 w-5" /> : <Send className="h-5 w-5" />}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="min-w-[800px] flex-1 items-center justify-center p-2">
        <ChatPreview message={messages[currentMessageIndex]} />
      </div>
      <Dialog open={openDialogConfirmTerminate} onOpenChange={setOpenDialogConfirmTerminate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Terminate Task</DialogTitle>
            <DialogDescription>Are you sure you want to terminate this task?</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenDialogConfirmTerminate(false)}>
              Cancel
            </Button>
            <Button
              onClick={async () => {
                await terminateTask({ taskId });
                router.refresh();
                setOpenDialogConfirmTerminate(false);
              }}
            >
              Terminate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
