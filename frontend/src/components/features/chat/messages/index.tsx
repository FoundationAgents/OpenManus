import { Markdown } from '@/components/block/markdown';
import { Badge } from '@/components/ui/badge';
import type { Message } from '@/libs/chat-messages';
import { cn } from '@/libs/utils';
import '@/styles/animations.css';

interface ChatMessageProps {
  messages: Message[];
}

const formatTime = (time: Date) => {
  return time.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

const StepBadge = ({ message }: { message: Message }) => {
  const eventType = message.type || 'unknown';
  const step = message.step || message.content.step_number;

  if (eventType === 'agent.agentstepstart') {
    return (
      <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs')}>
        <span className="thinking-animation">🤔</span>
        <span>Step {step} Thinking...</span>
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className={cn('text-muted-foreground cursor-pointer font-mono text-xs')}>
      <span>🚀</span>
      Step {step} Complete
    </Badge>
  );
};

const ChatMessage = ({ message, latest }: { message: Message; latest: boolean }) => {
  const agentName = message.content.agent_name || 'Manus';
  const result = message.content.result;
  const startTime = message.createdAt;

  const hidden = message.type === 'agent.agentstepstart' && !latest;

  if (hidden) return null;

  return (
    <div className="group mb-4 space-y-4">
      <div className="space-y-2">
        <div className="container mx-auto max-w-4xl">
          {/* Message Header */}
          <div className="mb-2 flex items-center justify-between">
            <div className="text-lg font-bold">✨ {agentName}</div>
            {startTime && (
              <div className="text-xs font-medium text-gray-500 italic opacity-0 transition-opacity duration-300 group-hover:opacity-100 hover:opacity-100">
                {formatTime(startTime)}
              </div>
            )}
          </div>

          {/* Step Badge */}
          <div className="text-muted-foreground mt-2 mb-2 font-mono text-xs">
            <StepBadge message={message} />
          </div>

          {/* Result */}
          {result && (
            <div className="flex flex-col gap-2 space-y-2">
              <Markdown className="chat">{result}</Markdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  console.log('messages', messages);
  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <div key={message.index || index} className="first:pt-0">
          <ChatMessage message={message} latest={index === messages.length - 1} />
        </div>
      ))}
    </div>
  );
};
