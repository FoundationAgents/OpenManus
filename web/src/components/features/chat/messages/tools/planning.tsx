import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { BrowserUseToolTooltip } from './browser-use-tool-message';
import { AggregatedMessage } from '@/types/chat';
import { useCurrentMessageIndex } from '@/app/tasks/hooks';
import Markdown from 'react-markdown';

export const PlanningTooltip = ({ args, result }: { args: any; result: { output: string } }) => {
  if (!result) return null;

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
      <div className="markdown-body chat mt-2 rounded-md p-4 text-xs">
        <Markdown>{result.output}</Markdown>
      </div>
    </div>
  );
};

export const PlanningMessage = ({
  args,
  result,
  message,
}: {
  args: any;
  result: { output: string };
  message: AggregatedMessage & { type: 'tool' };
}) => {
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const strReplaceExecuteStartMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:start');

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
          <span className="font-mono">
            {result ? '🎯' : '🚨'} Planning
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
        <PlanningTooltip args={args} result={result} />
      </PopoverContent>
    </Popover>
  );
};
