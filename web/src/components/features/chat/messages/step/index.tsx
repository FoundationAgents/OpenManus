import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Separator } from '@/components/ui/separator';
import { cn, formatNumber } from '@/lib/utils';
import { AggregatedMessage, Message } from '@/lib/chat-messages/types';

export const StepBadge = ({ message }: { message: AggregatedMessage & { type: 'agent:lifecycle:step' } }) => {
  if (message.type !== 'agent:lifecycle:step') return null;

  // 在一个step中查找think和act消息
  const thinkMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:think') as
    | (AggregatedMessage & { type: 'agent:lifecycle:step:think' })
    | undefined;

  const actMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:act') as
    | (AggregatedMessage & { type: 'agent:lifecycle:step:act' })
    | undefined;

  const stepStartMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:start') as AggregatedMessage & {
    type: 'agent:lifecycle:step:start';
  };

  const stepCompleteMessage = message?.messages.find(msg => msg.type === 'agent:lifecycle:step:complete') as AggregatedMessage & {
    type: 'agent:lifecycle:step:complete';
  };

  const thinkTokenCountMessage = thinkMessage?.messages.find(msg => msg.type === 'agent:lifecycle:step:think:token:count') as AggregatedMessage & {
    type: 'agent:lifecycle:step:think:token:count';
  };

  const actTokenCountMessage = actMessage?.messages.find(
    (msg): msg is Message => 'type' in msg && msg.type === 'agent:lifecycle:step:act:token:count',
  ) as AggregatedMessage & { type: 'agent:lifecycle:step:act:token:count' };

  const stepCount = stepStartMessage?.content.count || 0;

  const input = (thinkTokenCountMessage?.content.input || 0) + (actTokenCountMessage?.content.input || 0);
  const completion = (thinkTokenCountMessage?.content.completion || 0) + (actTokenCountMessage?.content.completion || 0);

  const totalInput = (actTokenCountMessage ?? thinkTokenCountMessage)?.content.total_input || 0;
  const totalCompletion = (actTokenCountMessage ?? thinkTokenCountMessage)?.content.total_completion || 0;

  return (
    <div className="text-muted-foreground mt-2 mb-2 font-mono text-xs">
      <Popover>
        <PopoverTrigger asChild>
          <Badge
            variant={stepCompleteMessage ? 'outline' : 'default'}
            className={cn('cursor-pointer font-mono text-xs', stepCompleteMessage && 'text-muted-foreground')}
          >
            {stepCompleteMessage ? (
              <>
                🚀 Step {stepCount} ({formatNumber(input, { autoUnit: true })} input; {formatNumber(completion, { autoUnit: true })} completion)
              </>
            ) : (
              <>
                <span className="thinking-animation">🤔</span>
                <span>Step {stepCount} Thinking...</span>
                <span>
                  Token Usage: {formatNumber(input, { autoUnit: true })} input; {formatNumber(completion, { autoUnit: true })} completion
                </span>
              </>
            )}
          </Badge>
        </PopoverTrigger>
        <PopoverContent>
          <div className="text-muted-foreground font-mono text-xs">
            Think Token Usage:{' '}
            <div>
              {formatNumber(thinkTokenCountMessage?.content.input || 0, { autoUnit: true })} input;{' '}
              {formatNumber(thinkTokenCountMessage?.content.completion || 0, { autoUnit: true })} completion
            </div>
          </div>
          <div className="text-muted-foreground mt-2 font-mono text-xs">
            Act Token Usage:{' '}
            <div>
              {formatNumber(actTokenCountMessage?.content.input || 0, { autoUnit: true })} input;{' '}
              {formatNumber(actTokenCountMessage?.content.completion || 0, { autoUnit: true })} completion
            </div>
          </div>
          {totalInput || totalCompletion ? (
            <>
              <Separator className="my-2" />
              <div className="text-muted-foreground font-mono text-xs">
                Cumulative Token Usage (All Steps):{' '}
                <div>
                  {formatNumber(totalInput, { autoUnit: true })} input; {formatNumber(totalCompletion, { autoUnit: true })} completion
                </div>
              </div>
            </>
          ) : null}
        </PopoverContent>
      </Popover>
    </div>
  );
};
