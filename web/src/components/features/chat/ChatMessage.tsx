import { Message } from '@/types/chat';
import Markdown from 'react-markdown';
import { CollapsibleMessage } from '@/components/features/chat/CollapsibleMessage';
import { useMemo } from 'react';
import { Badge } from '@/components/ui/badge';

interface ChatMessageProps {
  message: Message;
}

const renderUserMessage = (message: Message) => (
  <div className="border-l-2 border-muted">
    <div className="prose prose-sm prose-neutral dark:prose-invert">
      <Markdown>{message.content}</Markdown>
    </div>
  </div>
);

const renderAgentMessage = (message: Message) => {
  const [title, ...content] = message.content.split('\n');
  return (
    <div className="text-sm text-foreground">
      <div className="prose prose-sm prose-neutral dark:prose-invert">
        <div>{title}</div>
        <div className="pl-6 pt-2">
          <Markdown>{content.join('\n')}</Markdown>
        </div>
      </div>
    </div>
  );
};

const renderStepMessage = (message: Message) => {
  return (
    <div className="mt-2 text-sm text-muted-foreground">
      <Badge variant="outline">{message.content}</Badge>
    </div>
  );
};

const renderToolProgressMessage = (message: Message) => {
  return <div className="pl-6 text-sm text-muted-foreground">{message.content}</div>;
};

const renderToolCompletedMessage = (message: Message) => {
  const [title, content] = message.content.split(' Result: ');
  return (
    <div className="pl-6 text-sm text-muted-foreground">
      <CollapsibleMessage title={title} content={content} defaultExpanded={false} className="prose-sm" />
    </div>
  );
};

const renderCollapsibleMessage = (message: Message) => {
  const [title, ...content] = message.content.split('\n');
  return (
    <div className="mt-2 text-sm text-muted-foreground">
      <CollapsibleMessage title={title} content={content.join('\n')} defaultExpanded={false} className="prose-sm" />
    </div>
  );
};

const renderAssistantMessage = (message: Message) => {
  // Handle different message types
  switch (message.type) {
    case 'think':
    case 'complete':
    case 'error':
      return renderAgentMessage(message);
    case 'tool:selected':
    case 'tool:prepared':
    case 'tool:arguments':
    case 'tool:activating':
      return renderToolProgressMessage(message);
    case 'tool:completed':
      return renderToolCompletedMessage(message);
    case 'step':
      return renderStepMessage(message);
    case 'log':
      return null;
    default:
      return renderCollapsibleMessage(message);
  }
};

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const messageConfig = useMemo(() => {
    // First distinguish between user and assistant messages by role
    if (message.role === 'user') {
      return { component: renderUserMessage(message) };
    }

    // Render assistant message based on type
    return { component: renderAssistantMessage(message) };
  }, [message.role, message.type, message.content]);

  return (
    <div className="first:pt-0">
      <div className="container max-w-2xl mx-auto">{messageConfig.component}</div>
    </div>
  );
};
