import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { BrowserUseToolTooltip } from './browser-use-tool-message';
import { AggregatedMessage } from '@/types/chat';
import { useCurrentMessageIndex } from '@/app/tasks/hooks';
import Link from 'next/link';

export const StrReplaceEditorTooltip = ({ args, result }: { args: any; result: string }) => {
  if (!result) return null;

  const filePath = result.match(/File created successfully at: ([^\s]+)/)?.[1];

  return (
    <div className="space-y-2">
      <div className="flex flex-col flex-wrap gap-2 text-wrap">
        {Object.entries(args).map(([key, value]) => (
          <div key={key} className="text-sm">
            <Badge variant="outline" className="cursor-pointer font-medium">
              {key}
            </Badge>
            <pre className="mt-1 ml-2 space-y-1 text-wrap">{typeof value === 'string' ? value : JSON.stringify(value)}</pre>
          </div>
        ))}
      </div>
      <div className="text-sm">
        <Badge variant="outline" className="font-medium">
          File created successfully at
        </Badge>
        <pre className="mt-1 ml-2 space-y-1 text-wrap">{filePath}</pre>
      </div>
    </div>
  );
};

export const StrReplaceEditorMessage = ({ args, result, message }: { args: any; result: string; message: AggregatedMessage & { type: 'tool' } }) => {
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const strReplaceExecuteStartMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:start');

  if (args.command === 'view') {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
            <span className="font-mono">
              {result ? '🎯' : '🚨'} Viewing file:{' '}
              <span
                className="cursor-pointer hover:underline"
                onClick={e => {
                  e.preventDefault();
                  setCurrentMessageIndex(strReplaceExecuteStartMessage?.index ?? currentMessageIndex);
                }}
              >
                {strReplaceExecuteStartMessage?.content.args.path}
              </span>
            </span>
          </Badge>
        </PopoverTrigger>
        <PopoverContent className="w-auto" align="start">
          <StrReplaceEditorTooltip args={args} result={result} />
        </PopoverContent>
      </Popover>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
          <span className="font-mono">
            {result ? '🎯' : '🚨'} Editing file:{' '}
            <span
              className="cursor-pointer hover:underline"
              onClick={e => {
                e.preventDefault();
                setCurrentMessageIndex(strReplaceExecuteStartMessage?.index ?? currentMessageIndex);
              }}
            >
              {strReplaceExecuteStartMessage?.content.args.path}
            </span>
          </span>
        </Badge>
      </PopoverTrigger>
      <PopoverContent className="w-auto" align="start">
        <StrReplaceEditorTooltip args={args} result={result} />
      </PopoverContent>
    </Popover>
  );
};
