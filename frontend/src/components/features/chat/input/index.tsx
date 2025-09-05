import { confirm } from '@/components/block/confirm';
import { Button } from '@/components/ui/button';
import { DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { PauseCircle, Rocket, Send } from 'lucide-react';
import { useState } from 'react';

interface ChatInputProps {
  taskId?: string;
  status?: 'idle' | 'thinking' | 'terminating' | 'completed';
  onSubmit?: (value: { taskId?: string; prompt: string }) => Promise<void>;
  onTerminate?: () => Promise<void>;
}

export const ChatInput = ({ taskId, status = 'idle', onSubmit, onTerminate }: ChatInputProps) => {
  const [value, setValue] = useState('');

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (status === 'thinking' || status === 'terminating' || !value.trim()) {
        return;
      }
      await onSubmit?.({ taskId, prompt: value.trim() });
      setValue('');
    }
  };

  const handleSendClick = async () => {
    if (status === 'thinking' || status === 'terminating') {
      confirm({
        content: (
          <DialogHeader>
            <DialogTitle>Terminate Task</DialogTitle>
            <DialogDescription>Are you sure you want to terminate this task?</DialogDescription>
          </DialogHeader>
        ),
        onConfirm: async () => {
          await onTerminate?.();
        },
        buttonText: {
          cancel: 'Cancel',
          confirm: 'Terminate',
          loading: 'Terminating...',
        },
      });
      return;
    }
    const v = value.trim();
    if (v) {
      await onSubmit?.({ prompt: v });
      setValue('');
    }
  };

  return (
    <div className="pointer-events-none absolute right-0 bottom-0 left-0 p-4">
      <div className="pointer-events-auto mx-auto flex w-full max-w-2xl flex-col gap-2">
        {status !== 'idle' && (
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              className="flex cursor-pointer items-center gap-2 rounded-full"
              type="button"
              onClick={() => (window.location.href = '/')}
            >
              <Rocket className="h-4 w-4" />
              <span>New Task</span>
            </Button>
          </div>
        )}
        <div className="bg-background dark:bg-background flex w-full flex-col rounded-2xl shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:border">
          <Textarea
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={status === 'thinking' || status === 'terminating'}
            placeholder={
              status === 'thinking'
                ? 'Thinking...'
                : status === 'terminating'
                  ? 'Terminating...'
                  : status === 'completed'
                    ? 'Task completed!'
                    : 'No fortress, purely open ground. OpenManus is Coming.'
            }
            className="min-h-[80px] flex-1 resize-none border-none bg-transparent px-4 py-3 shadow-none outline-none focus-visible:ring-0 focus-visible:ring-offset-0 dark:bg-transparent"
          />
          <div className="border-border flex items-center justify-between border-t px-4 py-2">
            <div />
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 cursor-pointer rounded-xl"
                onClick={handleSendClick}
                disabled={status !== 'idle' && status !== 'completed' && !(status === 'thinking' || status === 'terminating')}
                aria-label={status === 'thinking' || status === 'terminating' ? 'Terminate task' : 'Send message'}
              >
                {status === 'thinking' || status === 'terminating' ? <PauseCircle className="h-4 w-4" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
