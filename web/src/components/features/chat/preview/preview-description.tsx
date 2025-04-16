import { Badge } from '@/components/ui/badge';
import { CardDescription } from '@/components/ui/card';
import { Message } from '@/lib/chat-messages/types';
import { usePreviewData } from './store';
interface ChatPreviewDescriptionProps {
  messages: Message[];
}

export const PreviewDescription = ({ messages }: ChatPreviewDescriptionProps) => {
  const { data } = usePreviewData();

  if (data?.type === 'tool') {
    const executionStart = messages.find(m => m.type === 'agent:lifecycle:step:act:tool:execute:start' && m.content.id === data.toolId);
    return (
      <CardDescription className="text-sm">
        Manus is using Tool <Badge variant="outline">{executionStart?.content.name}</Badge> <code>{executionStart?.content.id}</code>
      </CardDescription>
    );
  }

  if (data?.type === 'browser') {
    return (
      <CardDescription className="text-sm">
        Manus is browsing{' '}
        <a href={data.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
          {data.title}
        </a>
      </CardDescription>
    );
  }

  return <CardDescription className="text-sm">Manus is not using the computer right now...</CardDescription>;
};
