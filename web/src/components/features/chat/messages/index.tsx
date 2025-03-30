import { Message, AggregatedMessage } from '@/types/chat';
import Markdown from 'react-markdown';
import { Badge } from '@/components/ui/badge';
import { getBase64ImageUrl } from '@/lib/image';
import Link from 'next/link';
import { useCurrentMessageIndex } from '@/app/tasks/hooks';
import { ToolMessage } from './tools';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
interface ChatMessageProps {
  messages: Message[];
}

const renderUserMessage = (message: Message<{ prompt: string }>) => (
  <div className="border-muted border-l-2">
    <div className="prose prose-sm prose-neutral dark:prose-invert">
      <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
        {message.content.prompt}
      </Markdown>
    </div>
  </div>
);

const renderStepMessage = (message: Message) => {
  return <div className="text-muted-foreground mt-2 text-xs">{message.step}</div>;
};

const renderCompleteMessage = (message: Message<{ results: string[] }>) => {
  return (
    <div className="mt-2 text-xs">
      <Badge variant="outline" className="cursor-pointer font-mono">
        🎯 Task Completed
      </Badge>
    </div>
  );
};

const renderToolSelectedMessage = (message: Message) => {
  return (
    <div className="container mx-auto max-w-2xl">
      <div className="mb-2 flex items-center gap-2">
        <div className="text-lg font-bold">✨ Manus</div>
      </div>
      {message.content.thoughts && (
        <div className="markdown-body chat mt-2 rounded-md p-4 text-xs">
          <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {message.content.thoughts}
          </Markdown>
        </div>
      )}
    </div>
  );
};

/**
 * Aggregate tool messages into a single message with a list of tool calls
 *
 * a tool is started by a 'agent:tool:selected' message, and ends by a 'agent:tool:complete' message
 * a tool may be called multiple times, and each call is an 'agent:tool:start' and 'agent:tool:complete' message
 * a tool call timeline such as:
 *
 * agent:tool:selected (select 2 tools)
 *  |- agent:tool:start (start tool 1)
 *    |- agent:tool:execute:start (1)
 *    |- agent:tool:execute:complete (1)
 *  |- agent:tool:complete (complete tool 1)
 *  |- agent:tool:start (start tool 2)
 *    |- agent:tool:execute:start (2)
 *    |- agent:tool:execute:complete (2)
 *  |- agent:tool:complete (complete tool 2)
 *
 * @param messages
 * @returns
 */
const aggregateMessages = (messages: Message[]): AggregatedMessage[] => {
  const result = messages.reduce((acc, current) => {
    if (['agent:tool:start'].includes(current.type!)) {
      // need to create a new aggregatec message
      acc.push({ ...current, role: 'assistant', type: 'tool', messages: [current] });
      return acc;
    }
    if (
      [
        'agent:tool:execute:start',
        'agent:tool:execute:complete',
        'agent:tool:complete',
        'agent:tool:error',
        'agent:browser:browse:start',
        'agent:browser:browse:complete',
      ].includes(current.type!)
    ) {
      // find the nearest agent:tool:start from the end
      const selectedMessage = acc.findLast(msg => msg.type === 'tool');
      if (selectedMessage) {
        (selectedMessage as { messages: Message[] }).messages.push(current);
      }
      return acc;
    }
    acc.push(current);
    return acc;
  }, [] as AggregatedMessage[]);

  return result;
};

const ChatMessage = (props: { message: AggregatedMessage }) => {
  const { message } = props;
  if (message.role === 'user') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-2xl">{renderUserMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:lifecycle:complete') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-2xl">{renderCompleteMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:tool:selected') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-2xl">{renderToolSelectedMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'tool') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-2xl">
          <ToolMessage message={message} />
        </div>
      </div>
    );
  }
  if (message.type === 'agent:step:start') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-2xl">{renderStepMessage(message)}</div>
      </div>
    );
  }
  return null;
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  const m = aggregateMessages(messages.map((msg, index) => ({ ...msg, index })));
  return m
    .map(message => {
      return (
        <div key={message.index}>
          <ChatMessage message={message} />
        </div>
      );
    })
    .filter(Boolean);
};
