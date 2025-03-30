import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { AggregatedMessage } from '@/types/chat';
import { useCurrentMessageIndex } from '@/app/tasks/hooks';

export const PythonExecuteTooltip = ({
  args,
  result,
}: {
  args: any;
  result: {
    error: string | null;
    output: string;
    system: string | null;
    base64_image: string | null;
  };
}) => {
  if (!result) return null;

  const filePath = result.output?.match(/File created successfully at: ([^\s]+)/)?.[1];

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

export const PythonExecuteMessage = ({
  args,
  result,
  message,
}: {
  args: any;
  result: { error: string | null; output: string; system: string | null; base64_image: string | null };
  message: AggregatedMessage & { type: 'tool' };
}) => {
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const executeStartMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:start');
  const executeCompleteMessage = message.messages.find(msg => msg.type === 'agent:tool:execute:complete');
  return (
    <>
      <Popover>
        <PopoverTrigger asChild>
          <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
            <span className="font-mono">
              {executeStartMessage && (
                <span
                  className="cursor-pointer font-mono hover:underline"
                  onClick={e => {
                    e.preventDefault();
                    setCurrentMessageIndex(executeStartMessage.index ?? currentMessageIndex);
                  }}
                >
                  {!result ? '🔍' : result.error ? '🚨' : '🎯'} Python executing...
                </span>
              )}
            </span>
            {executeCompleteMessage && (
              <span
                className="cursor-pointer font-mono hover:underline"
                onClick={e => {
                  e.preventDefault();
                  setCurrentMessageIndex(executeCompleteMessage.index ?? currentMessageIndex);
                }}
              >
                Completed
              </span>
            )}
          </Badge>
        </PopoverTrigger>
        <PopoverContent className="w-md max-w-md" align="start">
          <PythonExecuteTooltip args={args} result={result} />
        </PopoverContent>
      </Popover>
    </>
  );
};
