import { confirm } from '@/components/block/confirm';
import { ToolsConfigDialog, useSelectedTools } from '@/components/features/tools/tools-config-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { shareTask } from '@/actions/tasks';
import { Paperclip, PauseCircle, Rocket, Send, Share2, Wrench, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { useConfigDialog } from '../../config/config-dialog';
import { useLlmConfig } from '../../config/config-llm';

interface ChatInputProps {
  status?: 'idle' | 'thinking' | 'terminating' | 'completed';
  onSubmit?: (value: { prompt: string; tools: string[]; files: File[] }) => Promise<void>;
  onTerminate?: () => Promise<void>;
  taskId?: string;
}

export const ChatInput = ({ status = 'idle', onSubmit, onTerminate, taskId }: ChatInputProps) => {
  const router = useRouter();

  const { config, loading } = useLlmConfig();
  const { show: showConfig } = useConfigDialog();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const [value, setValue] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [toolsConfigDialogOpen, setToolsConfigDialogOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareExpiration, setShareExpiration] = useState('60');
  const [isSharing, setIsSharing] = useState(false);
  const { selected: selectedTools, setSelected: setSelectedTools } = useSelectedTools();

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (status === 'thinking' || status === 'terminating' || !value.trim()) {
        return;
      }
      await onSubmit?.({ prompt: value.trim(), tools: selectedTools, files });
      setValue('');
      setFiles([]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      e.target.value = '';
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleSendClick = async () => {
    if (!config) {
      showConfig();
      return;
    }
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
          router.refresh();
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
    if (v || files.length > 0) {
      await onSubmit?.({ prompt: v, tools: selectedTools, files });
      setValue('');
      setFiles([]);
    }
  };

  const handleShareClick = () => {
    setShareDialogOpen(true);
  };

  const handleShare = async () => {
    if (!taskId) return;

    setIsSharing(true);
    try {
      const daysToMs = parseInt(shareExpiration) * 24 * 60 * 60 * 1000;
      const expiresAt = Date.now() + daysToMs;
      await shareTask({ taskId, expiresAt });
      navigator.clipboard.writeText(shareUrl);
      toast.success('Share Link Copied');
    } catch (error) {
      console.error('Error sharing task:', error);
    } finally {
      setIsSharing(false);
    }
  };

  const shareUrl = typeof window !== 'undefined' ? `${window.location.origin}/share/tasks/${taskId}` : '';

  return (
    <div className="pointer-events-none absolute right-0 bottom-0 left-0 p-4">
      <div className="pointer-events-auto mx-auto flex w-full max-w-2xl flex-col gap-2">
        {status !== 'idle' && (
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              className="flex cursor-pointer items-center gap-2 rounded-full"
              type="button"
              onClick={() => router.push('/tasks')}
            >
              <Rocket className="h-4 w-4" />
              <span>New Task</span>
            </Button>
            {taskId && status === 'completed' && (
              <Button variant="outline" className="flex cursor-pointer items-center gap-2 rounded-full" type="button" onClick={handleShareClick}>
                <Share2 className="h-4 w-4" />
                <span>Share</span>
              </Button>
            )}
          </div>
        )}
        {!config && loading === false && (
          <div className="flex justify-center">
            <Button variant="outline" className="flex cursor-pointer items-center gap-2 rounded-full" type="button" onClick={showConfig}>
              <Wrench className="h-4 w-4" />
              <span>Please configure your LLM model first</span>
            </Button>
          </div>
        )}
        <div className="flex w-full flex-col rounded-2xl bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)]">
          <Textarea
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={status === 'thinking' || status === 'terminating' || !config}
            placeholder={
              status === 'thinking'
                ? 'Thinking...'
                : status === 'terminating'
                  ? 'Terminating...'
                  : status === 'completed'
                    ? 'Task completed!'
                    : "Let's Imagine the Impossible, Create the Future Together"
            }
            className="min-h-[80px] flex-1 resize-none border-none bg-transparent px-4 py-3 shadow-none outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          <div className="flex items-center justify-between border-t border-gray-100 px-4 py-2">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="flex cursor-pointer items-center gap-1" onClick={() => setToolsConfigDialogOpen(true)}>
                <Wrench className="h-3 w-3" />
                <span>Tools {selectedTools.length ? `(${selectedTools.length})` : ''}</span>
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {files.length > 0 && (
                <Badge variant="secondary" className="flex cursor-default items-center gap-1 py-1 pr-1 pl-2">
                  <span>
                    {files.length} File{files.length > 1 ? 's' : ''}
                  </span>
                  <Badge
                    variant="secondary"
                    className="hover:bg-muted-foreground/20 ml-1 flex h-4 w-4 cursor-pointer items-center justify-center rounded-full p-0"
                    onClick={() => setFiles([])}
                    aria-label="Clear selected files"
                  >
                    <X className="text-muted-foreground h-3 w-3" />
                  </Badge>
                </Badge>
              )}
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 cursor-pointer rounded-xl hover:bg-gray-100"
                disabled={!config}
                onClick={triggerFileSelect}
                aria-label="Attach files"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <input type="file" ref={fileInputRef} multiple onChange={handleFileSelect} className="hidden" accept="*" />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 cursor-pointer rounded-xl hover:bg-gray-100"
                onClick={handleSendClick}
                disabled={status !== 'idle' && status !== 'completed' && !(status === 'thinking' || status === 'terminating') && !config}
                aria-label={status === 'thinking' || status === 'terminating' ? 'Terminate task' : 'Send message'}
              >
                {status === 'thinking' || status === 'terminating' ? <PauseCircle className="h-4 w-4" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </div>
      </div>
      <ToolsConfigDialog
        open={toolsConfigDialogOpen}
        onOpenChange={setToolsConfigDialogOpen}
        selected={selectedTools}
        onSelected={setSelectedTools}
      />

      <Dialog open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
        <DialogContent
          style={{ maxWidth: '600px' }}
          onEscapeKeyDown={e => {
            e.preventDefault();
          }}
          onOpenAutoFocus={e => {
            e.preventDefault();
            if (document.activeElement instanceof HTMLElement) {
              document.activeElement.blur();
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>Share Task</DialogTitle>
            <DialogDescription>Share this task</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <Input value={shareUrl} readOnly className="w-full" />

            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label htmlFor="expiration" className="mb-1 block text-sm text-gray-500">
                  Duration
                </label>
                <Select value={shareExpiration} onValueChange={setShareExpiration}>
                  <SelectTrigger id="expiration" className="w-full">
                    <SelectValue placeholder="Select duration" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 days</SelectItem>
                    <SelectItem value="30">30 days</SelectItem>
                    <SelectItem value="60">60 days</SelectItem>
                    <SelectItem value="180">180 days</SelectItem>
                    <SelectItem value="365">365 days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter className="flex justify-end">
            <Button onClick={handleShare} disabled={isSharing}>
              {isSharing ? 'Processing...' : 'Create Share Link and Copy'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
