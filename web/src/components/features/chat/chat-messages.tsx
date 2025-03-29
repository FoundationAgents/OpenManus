import { Message, AggregatedMessage } from '@/types/chat';
import Markdown from 'react-markdown';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BrowserUseToolMessage } from './browser-use-tool-message';
import { useMemo } from 'react';
import Image from 'next/image';
import { getBase64ImageUrl } from '@/lib/image';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { useCurrentMessageIndex } from '@/app/tasks/hooks';

interface ChatMessageProps {
  messages: Message[];
}

const renderUserMessage = (message: Message<{ prompt: string }>) => (
  <div className="border-l-2 border-muted">
    <div className="prose prose-sm prose-neutral dark:prose-invert">
      <Markdown>{message.content.prompt}</Markdown>
    </div>
  </div>
);

const renderAgentMessage = (message: Message) => {
  const [title, ...lines] = message.content.split('\n');
  const content = lines.join('\n');
  if (content === '') {
    return null;
  }

  return (
    <div className="text-sm text-foreground">
      <div className="prose prose-sm prose-neutral dark:prose-invert">
        <div>{title}</div>
        <div className="pt-2 markdown-content">
          <Markdown>{content}</Markdown>
        </div>
      </div>
    </div>
  );
};

const renderStepMessage = (message: Message) => {
  return <div className="mt-2 text-xs text-muted-foreground">{message.step}</div>;
};

const renderResultMessage = (message: Message<{ results: string[] }>) => {
  return (
    <div className="mt-2 text-xs markdown-content">
      <Markdown>{message.content.results.join('\n')}</Markdown>
    </div>
  );
};

const toolTypes = [
  'agent:tool:selected',
  'agent:tool:start',
  'agent:tool:complete',
  'agent:tool:error',
  'agent:tool:execute:start',
  'agent:tool:execute:complete',
];

const aggregateToolMessages = (messages: Message[]): AggregatedMessage[] => {
  const result = messages.reduce((acc, current) => {
    if (current.type === 'agent:tool:selected') {
      acc.push({ ...current, role: 'assistant', type: 'tool', messages: [current] });
      return acc;
    } else {
      (acc[acc.length - 1] as { messages: Message[] }).messages.push(current);
      return acc;
    }
  }, [] as AggregatedMessage[]);
  return result;
};

const BrowserMessage = ({
  message,
}: {
  message: Message<{
    url: string;
    tabs: string;
    title: string;
    results: string;
    screenshot: string;
    content_above: string;
    content_below: string;
  }>;
}) => {
  return (
    <div className="text-xs p-4 rounded-md border">
      <Link className="cursor-pointer hover:underline" href={message.content.url}>
        Browsing {message.content.title}
      </Link>
      {message.content.screenshot && (
        <img
          src={getBase64ImageUrl(message.content.screenshot)}
          alt={message.content.title}
          className="mt-2 cursor-pointer rounded object-cover object-top h-24 w-24"
        />
      )}
    </div>
  );
};

const renderToolProgressCard = (message: AggregatedMessage) => {
  if (message.type !== 'tool') return null;
  const selectedMessage = message.messages.find(msg => msg.type === 'agent:tool:selected')?.content as {
    thoughts: string;
    tool_calls: {
      id: string;
      type: 'function';
      index: number;
      function: {
        name: string;
        arguments: { query: string; action: string };
      };
    }[];
  };

  const completeMessages = message.messages.filter(msg => msg.type === 'agent:tool:execute:complete');

  const calls = selectedMessage?.tool_calls.map((call, index) => {
    const name = call.function.name;
    const args = call.function.arguments;
    const completeContent = completeMessages[index]?.content as { result: string };
    return { index, name, args, completeContent };
  });

  const isCompleted = completeMessages.length === calls.length;

  const popoverContent = ({ name, args, completeContent }: { name: string; args: any; completeContent: { result: string } }) => {
    if (name === 'browser_use') {
      return <BrowserUseToolMessage args={args} completeContent={completeContent} />;
    }
    return (
      <div>
        <div className="prose prose-sm prose-neutral dark:prose-invert flex flex-wrap gap-2">
          {Object.entries(args).map(([key, value]) => (
            <div key={key}>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Badge variant="outline" className="cursor-pointer">
                      {key}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent>
                    <pre>{typeof value === 'string' ? value : JSON.stringify(value, null, 2)}</pre>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          ))}
        </div>
        <div>
          <div className="mt-2">{completeContent?.result}</div>
        </div>
      </div>
    );
  };

  return (
    <div>
      {calls.map(call => {
        return (
          <Popover key={call.index}>
            <PopoverTrigger asChild>
              <Badge variant="outline" className="flex items-center gap-2 cursor-pointer">
                <span className="font-mono">
                  {isCompleted ? '🎯' : '🚨'} {call.name}
                </span>
              </Badge>
            </PopoverTrigger>
            <PopoverContent className="max-w-md w-md" align="start">
              {popoverContent(call)}
            </PopoverContent>
          </Popover>
        );
      })}
    </div>
  );
};

const ChatMessage = (props: { message: AggregatedMessage }) => {
  const { message } = props;
  if (message.role === 'user') {
    return (
      <div className="first:pt-0">
        <div className="container max-w-2xl mx-auto">{renderUserMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:lifecycle:complete') {
    return (
      <div className="first:pt-0">
        <div className="container max-w-2xl mx-auto">{renderResultMessage(message)}</div>
      </div>
    );
  }
  if (message.type === 'tool') {
    return (
      <div className="first:pt-0">
        <div className="container max-w-2xl mx-auto">{renderToolProgressCard(message)}</div>
      </div>
    );
  }
  if (message.type === 'agent:browser:browse:complete') {
    return (
      <div className="first:pt-0">
        <div className="container max-w-2xl mx-auto">
          <BrowserMessage message={message} />
        </div>
      </div>
    );
  }
  if (message.type === 'agent:step:start') {
    return (
      <div className="first:pt-0">
        <div className="container max-w-2xl mx-auto">{renderStepMessage(message)}</div>
      </div>
    );
  }
  return null;
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  const messagesWithIndex = messages.map((msg, index) => ({ ...msg, index }));
  const toolChainMessages = messagesWithIndex.filter(msg => toolTypes.includes(msg.type || ''));
  const notToolMessages = messagesWithIndex.filter(msg => !toolTypes.includes(msg.type || ''));
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();

  const toolMessages = aggregateToolMessages(toolChainMessages);

  return ([...notToolMessages, ...toolMessages] as AggregatedMessage[])
    .sort((a, b) => (a.index ?? -1) - (b.index ?? -1))
    .map(message => {
      return (
        <div key={message.index} onClick={() => setCurrentMessageIndex(message.index ?? currentMessageIndex)}>
          <ChatMessage message={message} />
        </div>
      );
    })
    .filter(Boolean);
};
