import { Markdown } from '@/components/block/markdown';
import { Badge } from '@/components/ui/badge';
import type { AggregatedMessage, Message } from '@/libs/chat-messages/types';
import { formatNumber } from '@/libs/utils';
import '@/styles/animations.css';
import { StepBadge } from './step';
import { ToolMessageContent } from './tools';

interface ChatMessageProps {
  messages: AggregatedMessage[];
}

const UserMessage = ({ message }: { message: Message<{ request: string }> }) => <Markdown className="chat">{message.content.request}</Markdown>;

interface CompletionMessageProps {
  message: Message<{ results: string[]; total_input_tokens: number; total_completion_tokens: number }>;
}

const CompletionMessage = ({ message }: CompletionMessageProps) => {
  const showTokenCount = message.content.total_input_tokens || message.content.total_completion_tokens;
  return (
    <Badge className="cursor-pointer font-mono">
      🎉 Awesome! Task Completed{' '}
      {showTokenCount && (
        <>
          (
          <span>
            {formatNumber(message.content.total_input_tokens || 0, { autoUnit: true })} input;{' '}
            {formatNumber(message.content.total_completion_tokens || 0, { autoUnit: true })} completion
          </span>
          )
        </>
      )}
    </Badge>
  );
};

interface TerminatedMessageProps {
  message: Message<{ total_input_tokens?: number; total_completion_tokens?: number }>;
}

const TerminatedMessage = ({ message }: TerminatedMessageProps) => {
  const showTokenCount = message.content.total_input_tokens || message.content.total_completion_tokens;
  return (
    <Badge className="cursor-pointer font-mono">
      🚫 Task Terminated By User{' '}
      {showTokenCount && (
        <>
          (
          <span>
            {formatNumber(message.content.total_input_tokens || 0, { autoUnit: true })} input;{' '}
            {formatNumber(message.content.total_completion_tokens || 0, { autoUnit: true })} completion
          </span>
          )
        </>
      )}
    </Badge>
  );
};

const StepMessage = ({ message }: { message: AggregatedMessage & { type: 'agent:lifecycle:step' } }) => {
  if (!('messages' in message)) return null;

  const thinkMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:think') as
    | (AggregatedMessage & { type: 'agent:lifecycle:step:think' })
    | undefined;

  const toolSelectedMessage = thinkMessage?.messages.find(
    (msg): msg is Message => 'type' in msg && msg.type === 'agent:lifecycle:step:think:tool:selected',
  ) as (AggregatedMessage & { type: 'agent:lifecycle:step:think:tool:selected' }) | undefined;

  return (
    <div className="group mb-4 space-y-4">
      {thinkMessage && (
        <div className="space-y-2">
          <div className="container mx-auto max-w-4xl">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-lg font-bold">✨ Manus</div>
              <div className="text-xs font-medium text-gray-500 italic opacity-0 transition-opacity duration-300 group-hover:opacity-100 hover:opacity-100">
                {thinkMessage.createdAt
                  ? new Date(thinkMessage.createdAt).toLocaleString('zh-CN', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })
                  : ''}
              </div>
            </div>
            <StepBadge message={message} />
            <div className="flex flex-col gap-2 space-y-2">
              {toolSelectedMessage?.content.content && <Markdown className="chat">{toolSelectedMessage?.content.content}</Markdown>}
              <ToolMessageContent message={message} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const LifecycleMessage = ({ message }: { message: AggregatedMessage }) => {
  if (!('messages' in message)) return null;

  return (
    <div className="space-y-4">
      {message.messages.map((msg, index) => {
        if (!('type' in msg)) return null;

        if (msg.type === 'agent:lifecycle:start') {
          return (
            <div key={index} className="container mx-auto flex max-w-4xl justify-end">
              <UserMessage message={msg as Message<{ request: string }>} />
            </div>
          );
        }

        if (msg.type === 'agent:lifecycle:complete') {
          return (
            <div key={index} className="container mx-auto max-w-4xl">
              <CompletionMessage message={msg as Message<{ results: string[]; total_input_tokens: number; total_completion_tokens: number }>} />
            </div>
          );
        }

        if (msg.type === 'agent:lifecycle:terminated') {
          return (
            <div key={index} className="container mx-auto max-w-4xl">
              <TerminatedMessage message={msg} />
            </div>
          );
        }

        if (msg.type === 'agent:lifecycle:step') {
          return (
            <div key={index} className="container mx-auto max-w-4xl">
              <StepMessage message={msg as AggregatedMessage & { type: 'agent:lifecycle:step' }} />
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};

const ChatMessage = ({ message }: { message: AggregatedMessage }) => {
  if (!message.type?.startsWith('agent:lifecycle')) {
    return (
      <div className="container mx-auto max-w-4xl">
        <Markdown>{message.content}</Markdown>
      </div>
    );
  }

  return <LifecycleMessage message={message} />;
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <div key={message.index || index} className="first:pt-0">
          <ChatMessage message={message} />
        </div>
      ))}
    </div>
  );
};
