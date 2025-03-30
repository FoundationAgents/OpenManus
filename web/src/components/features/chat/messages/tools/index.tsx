import { AggregatedMessage } from '@/types/chat';
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
import { StrReplaceEditorMessage } from './str_replace_editor';
import { PythonExecuteMessage } from './python-execute-message';

export const ToolMessage = ({ message }: { message: AggregatedMessage }) => {
  if (message.type !== 'tool') return null;

  const executeStartMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:start');
  const executeCompleteMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:complete');

  const toolName = executeStartMessage?.content.name;
  const args = executeStartMessage?.content.args || {};
  const result = executeCompleteMessage?.content.result;

  if (toolName === 'browser_use') {
    return <BrowserUseToolMessage args={args} result={result} message={message} />;
  }

  if (toolName === 'str_replace_editor') {
    return <StrReplaceEditorMessage args={args} result={result} message={message} />;
  }

  if (toolName === 'python_execute') {
    return <PythonExecuteMessage args={args} result={result} message={message} />;
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
          <span className="font-mono">
            {result ? '🎯' : '🚨'} {toolName}
          </span>
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="w-auto" align="start">
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
          <div className="mt-2">{result}</div>
        </div>
      </PopoverContent>
    </Popover>
  );
};
