import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Message } from '@/lib/chat-messages/types';
import { PreviewContent } from './preview-content';
import { PreviewDescription } from './preview-description';
import { Button } from '@/components/ui/button';
import { FolderIcon } from 'lucide-react';
import { usePreviewData } from './store';

interface ChatPreviewProps {
  messages: Message[];
  taskId: string;
}

export const ChatPreview = ({ messages, taskId }: ChatPreviewProps) => {
  const { setData } = usePreviewData();
  return (
    <Card className="flex h-full flex-col gap-0 px-2">
      <CardHeader className="flex-none p-2 py-1">
        <div className="flex items-center justify-between">
          <CardTitle className="text-normal">Manus's Computer</CardTitle>
          <Button
            variant="outline"
            size="sm"
            className="hover:bg-accent/80 flex items-center gap-1.5"
            onClick={() => setData({ type: 'workspace', path: `${taskId}` })}
          >
            <FolderIcon className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">Task Workspace</span>
          </Button>
        </div>
        <PreviewDescription messages={messages} />
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-2">
        <div className="h-full w-full overflow-auto rounded-md">
          <PreviewContent messages={messages} />
        </div>
      </CardContent>
    </Card>
  );
};
