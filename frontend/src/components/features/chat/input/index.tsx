import { confirm } from '@/components/block/confirm';
import { Button } from '@/components/ui/button';
import { DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/libs/utils';
import { Loader2, PauseCircle, Send } from 'lucide-react';
import { useState } from 'react';

interface ChatInputProps {
  taskId?: string;
  status?: 'idle' | 'thinking' | 'terminating' | 'completed';
  onSubmit?: (value: { taskId?: string; prompt: string }) => Promise<void>;
  onTerminate?: () => Promise<void>;
  className?: string;
}

export const ChatInput = ({ taskId, status = 'idle', onSubmit, onTerminate, className }: ChatInputProps) => {
  const [value, setValue] = useState('');

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
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
    <div className={cn('pointer-events-none', className)}>
      <div className="pointer-events-auto mx-auto flex w-full max-w-2xl flex-col gap-2">
        {/* Input box */}
        <div className="bg-background dark:bg-background flex w-full flex-col rounded-2xl shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:border">
          <Textarea
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={status === 'thinking' || status === 'terminating'}
            placeholder="Type your message here..."
            className="min-h-[80px] flex-1 resize-none border-none bg-transparent px-4 py-3 shadow-none outline-none focus-visible:ring-0 focus-visible:ring-offset-0 dark:bg-transparent"
          />
          <div className="border-border flex items-center justify-between border-t px-4 py-2">
            {/* Status indicator */}
            <div className="flex items-center gap-2 text-xs text-gray-500"></div>

            {/* Send button */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 cursor-pointer rounded-xl"
                onClick={handleSendClick}
                disabled={!value.trim()}
                aria-label="Create task"
              >
                {status === 'thinking' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : status === 'terminating' ? (
                  <PauseCircle className="h-4 w-4" />
                ) : (
                  <Send className={`h-4 w-4 ${value.trim() ? '' : 'text-gray-400'}`} />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
