import { Button } from '@/components/ui/button';
import { CardTitle } from '@/components/ui/card';
import { FolderIcon } from 'lucide-react';
import { PreviewContent } from './preview-content';
import { usePreviewData } from './store';
import type { Message } from '@/libs/chat-messages';
import { cn } from '@/libs/utils';

interface ChatPreviewProps {
  messages: Message[];
  taskId: string;
  className?: string;
}

export const ChatPreview = ({ messages, taskId, className }: ChatPreviewProps) => {
  const { setData } = usePreviewData();
  return (
    <div className={cn('flex h-full flex-col gap-2 rounded-2xl border p-2', className)}>
      <div>
        <div className="flex items-center justify-between">
          <CardTitle className="text-normal">Manus's Computer</CardTitle>
          <Button
            variant="outline"
            size="sm"
            className="hover:bg-accent/80 bg-silver-gradient flex items-center gap-1.5"
            onClick={() => setData({ type: 'workspace', path: `${taskId}` })}
          >
            <FolderIcon className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">Task Workspace</span>
          </Button>
        </div>
      </div>
      <div className="h-full flex-1 overflow-hidden">
        <PreviewContent messages={messages} />

      </div>
    </div>
  );
};
