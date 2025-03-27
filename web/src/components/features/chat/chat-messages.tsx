import { Message, AggregatedMessage } from '@/types/chat';
import Markdown from 'react-markdown';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BrowserUseToolMessage } from './browser-use-tool-message';
import { useMemo } from 'react';

interface ChatMessageProps {
  messages: Message[];
}

const renderUserMessage = (message: Message) => (
  <div className="border-l-2 border-muted">
    <div className="prose prose-sm prose-neutral dark:prose-invert">
      <Markdown>{message.content}</Markdown>
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
  return <div className="mt-2 text-xs text-muted-foreground">{message.content}</div>;
};

const renderResultMessage = (message: Message) => {
  return (
    <div className="mt-2 text-xs markdown-content">
      <Markdown>{message.content}</Markdown>
    </div>
  );
};

const toolTypes = ['tool:selected', 'tool:prepared', 'tool:arguments', 'tool:activating', 'tool:completed'];

const aggregateToolMessages = (messages: Message[]): AggregatedMessage[] => {
  const result = messages.reduce((acc, current) => {
    if (current.type === 'tool:selected') {
      if (current.content.match(/selected 0 tools/i)) {
        return acc;
      } else {
        acc.push({ ...current, role: 'assistant', type: 'tool', messages: [current] });
        return acc;
      }
    } else {
      (acc[acc.length - 1] as { messages: Message[] }).messages.push(current);
      return acc;
    }
  }, [] as AggregatedMessage[]);
  return result;
};

const renderToolProgressCard = (message: AggregatedMessage) => {
  if (message.type !== 'tool') return null;
  const completedMessage = message.messages.find(msg => msg.type === 'tool:completed');
  const preparedMessage = message.messages.find(msg => msg.type === 'tool:prepared');
  const argsMessage = message.messages.find(msg => msg.type === 'tool:arguments');

  const isCompleted = !!completedMessage;

  let toolName: string = '';

  if (preparedMessage) {
    const toolsBeingPreparedMatch = preparedMessage.content.match(/Tools being prepared:?\s*\[(.*?)\]/i);
    if (toolsBeingPreparedMatch?.[1]) {
      const toolsStr = toolsBeingPreparedMatch[1];
      const toolMatch = toolsStr.match(/['"]([^'"]+)['"]/);
      if (toolMatch?.[1]) {
        toolName = toolMatch[1];
      }
    }
  }

  const popoverContent = () => {
    if (toolName === 'browser_use') {
      return <BrowserUseToolMessage message={message} />;
    }
    const args = JSON.parse(argsMessage?.content.match(/\{.*\}/)?.[0] || '{}');
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
          <div className="mt-2">{completedMessage?.content || ''}</div>
        </div>
      </div>
    );
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="outline" className="flex items-center gap-2 cursor-pointer">
          <span className="font-mono">
            {isCompleted ? '🎯' : '🚨'} {toolName}
          </span>
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="max-w-md w-md" align="start">
        {popoverContent()}
      </PopoverContent>
    </Popover>
  );
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  const messagesWithIndex = messages.map((msg, index) => ({ ...msg, index }));
  const toolChainMessages = messagesWithIndex.filter(msg => toolTypes.includes(msg.type || ''));
  const notToolMessages = messagesWithIndex.filter(msg => !toolTypes.includes(msg.type || ''));

  const toolMessages = aggregateToolMessages(toolChainMessages);

  return ([...notToolMessages, ...toolMessages] as AggregatedMessage[])
    .sort((a, b) => (a.index ?? -1) - (b.index ?? -1))
    .map((message, i) => {
      if (message.role === 'user') {
        return (
          <div key={`user-${i}`} className="first:pt-0">
            <div className="container max-w-2xl mx-auto">{renderUserMessage(message)}</div>
          </div>
        );
      }
      if (message.type === 'result') {
        return (
          <div key={`result-${i}`} className="first:pt-0">
            <div className="container max-w-2xl mx-auto">{renderResultMessage(message)}</div>
          </div>
        );
      }
      if (message.type === 'tool') {
        return (
          <div key={`tool-${i}`} className="first:pt-0">
            <div className="container max-w-2xl mx-auto">{renderToolProgressCard(message)}</div>
          </div>
        );
      }
      if (message.type === 'step') {
        return (
          <div key={`step-${i}`} className="first:pt-0">
            <div className="container max-w-2xl mx-auto">{renderStepMessage(message)}</div>
          </div>
        );
      }
      if (message.type === 'think' || message.type === 'error') {
        return (
          <div key={`think-${i}`} className="first:pt-0">
            <div className="container max-w-2xl mx-auto">{renderAgentMessage(message)}</div>
          </div>
        );
      }

      return null;
    })
    .filter(Boolean);
};
