import { Message, AggregatedMessage } from '@/types/chat';
import Markdown from 'react-markdown';
import { Badge } from '@/components/ui/badge';
import { ToolMessage } from './tools';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import '@/styles/animations.css';
import { StepMessage } from './step';
import { formatNumber } from '@/lib/utils';

interface ChatMessageProps {
  messages: Message[];
}

const renderStartMessage = (message: Message<{ request: string }>) => (
  <div className="markdown-body chat mt-2 rounded-md p-4">
    <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
      {message.content.request}
    </Markdown>
  </div>
);

const renderCompleteMessage = (message: Message<{ results: string[]; total_input_tokens: number; total_completion_tokens: number }>) => {
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

const renderTerminatedMessage = (message: Message) => {
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

const renderToolSelectedMessage = (message: Message) => {
  return (
    <div className="container mx-auto max-w-4xl">
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
    // Aggregate Tool Messages
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

    // Aggregate Step Messages
    if (['agent:step:start'].includes(current.type!)) {
      // need to create a new aggregatec message
      acc.push({ ...current, role: 'assistant', type: 'step', messages: [current] });
      return acc;
    }
    if (
      [
        'agent:think:start',
        'agent:think:token:count',
        'agent:think:complete',
        'agent:act:start',
        'agent:act:token:count',
        'agent:act:complete',
        'agent:step:complete',
      ].includes(current.type!)
    ) {
      // find the nearest agent:step:start from the end
      const selectedMessage = acc.findLast(msg => msg.type === 'step');
      if (selectedMessage) {
        (selectedMessage as { messages: Message[] }).messages.push(current);
      }
      return acc;
    }

    acc.push(current);
    return acc;
  }, [] as AggregatedMessage[]);

  // if step is last, add a thinking status to the last step
  // expect agent:browser:browse:start, it would be blocked at the first step for a while
  const list = result.filter(
    msg =>
      !(
        msg.type === 'agent:browser:browse:start' ||
        (msg.type === 'agent:browser:browse:error' && msg.content.error === 'Browser context not initialized')
      ),
  );
  const lastStep = list[list.length - 1];
  if (lastStep?.type === 'agent:step:start') {
    lastStep.content.thinking = true;
  }

  return result;
};

const ChatMessage = (props: { message: AggregatedMessage }) => {
  const { message } = props;
  if (message.type === 'agent:lifecycle:start') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto flex max-w-4xl justify-end">{renderStartMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:lifecycle:complete') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-4xl">{renderCompleteMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:lifecycle:terminated') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-4xl">{renderTerminatedMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:tool:selected') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-4xl">{renderToolSelectedMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'tool') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-4xl">
          <ToolMessage message={message as AggregatedMessage<'tool'>} />
        </div>
      </div>
    );
  }
  if (message.type === 'step') {
    return (
      <div className="first:pt-0">
        <div className="container mx-auto max-w-4xl">
          <StepMessage message={message as AggregatedMessage<'step'>} />
        </div>
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
