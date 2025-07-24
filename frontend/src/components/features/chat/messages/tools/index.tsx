import { Badge } from '@/components/ui/badge';
import type { AggregatedMessage, Message } from '@/libs/chat-messages/types';
import { getImageUrl } from '@/libs/image';
import { usePreviewData } from '../../preview/store';
import useAgentTools from '@/hooks/use-tools';

type ToolCall = {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: Record<string, any>;
  };
};

export const ToolMessageContent = ({ message }: { message: AggregatedMessage & { type: 'agent:lifecycle:step' } }) => {
  const { setData } = usePreviewData();
  const { getToolByPrefix } = useAgentTools();
  if (message.type !== 'agent:lifecycle:step') return null;

  // 在一个step中查找think和act消息
  const thinkMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:think') as
    | (AggregatedMessage & { type: 'agent:lifecycle:step:think' })
    | undefined;

  const actMessage = message.messages.find(msg => msg.type === 'agent:lifecycle:step:act') as
    | (AggregatedMessage & { type: 'agent:lifecycle:step:act' })
    | undefined;

  const toolSelectedMessage = thinkMessage?.messages.find(
    (msg): msg is Message => 'type' in msg && msg.type === 'agent:lifecycle:step:think:tool:selected',
  ) as (AggregatedMessage & { type: 'agent:lifecycle:step:think:tool:selected' }) | undefined;

  const browserMessage = thinkMessage?.messages.find(
    (msg): msg is Message => 'type' in msg && msg.type === 'agent:lifecycle:step:think:browser:browse:complete',
  ) as (AggregatedMessage & { type: 'agent:lifecycle:step:think:browser:browse:complete' }) | undefined;

  return (
    <div className="flex flex-col gap-2 space-y-2">
      <div className="flex flex-wrap gap-2">
        {toolSelectedMessage?.content.tool_calls &&
          toolSelectedMessage.content.tool_calls.map((toolCall: ToolCall) => {
            const actToolMessage = actMessage?.messages.find(m => m.type === 'agent:lifecycle:step:act:tool') as AggregatedMessage & {
              type: 'agent:lifecycle:step:act:tool';
            };
            const executeComplete = actToolMessage?.messages.find(
              m => m.type === 'agent:lifecycle:step:act:tool:execute:complete' && m.content.id === toolCall.id,
            );

            const { toolName, functionName } = getToolByPrefix(toolCall.function.name);

            return (
              <Badge
                key={toolCall.id}
                variant="outline"
                className="cursor-pointer font-mono font-medium"
                onClick={() => {
                  setData({ type: 'tool', toolId: toolCall.id });
                }}
              >
                {executeComplete?.content.error ? '🚨' : executeComplete ? '🎯' : <span className="searching-animation">🔍</span>} {toolName}{' '}
                {functionName}
              </Badge>
            );
          })}
      </div>
      {browserMessage && (
        <Badge variant="outline" className="cursor-pointer">
          <div className="relative my-1 h-24 w-24 overflow-hidden rounded">
            <img
              src={getImageUrl(browserMessage.content.screenshot)}
              onClick={() => {
                setData({
                  type: 'browser',
                  url: browserMessage.content.url,
                  title: browserMessage.content.title,
                  screenshot: browserMessage.content.screenshot,
                });
              }}
              alt={browserMessage.content.title || 'Screenshot'}
              className="h-full w-full cursor-pointer object-cover object-top"
              onError={(e: React.SyntheticEvent<HTMLImageElement, Event>) => {
                e.currentTarget.style.display = 'none';
                const parentNode = e.currentTarget.parentNode;
                const existingIcon = parentNode?.querySelector('.image-fallback-icon');
                if (!existingIcon) {
                  const iconContainer = document.createElement('div');
                  iconContainer.className = 'my-1 h-24 w-24 flex items-center justify-center rounded bg-muted image-fallback-icon';
                  iconContainer.innerHTML =
                    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-image"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>';
                  parentNode?.appendChild(iconContainer);
                }
              }}
            />
          </div>
        </Badge>
      )}
    </div>
  );
};
