import { Badge } from '@/components/ui/badge';
import type { AggregatedMessage, Message } from '@/libs/chat-messages/types';
import { getImageUrl } from '@/libs/image';
import { usePreviewData } from '../../preview/store';
import useAgentTools from '@/hooks/use-tools';
import { CheckCircle2, Loader2, TriangleAlert, Wrench } from 'lucide-react';

type ToolCall = {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: Record<string, unknown> | string;
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

  const renderDiff = (lines: string[]) => {
    if (!lines.length) return null;
    return (
      <div className="mt-2 overflow-x-auto rounded border bg-zinc-950/95 p-2 font-mono text-[11px] leading-5">
        {lines.map((line, idx) => {
          const cls = line.startsWith('+')
            ? 'text-emerald-300'
            : line.startsWith('-')
              ? 'text-rose-300'
              : line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')
                ? 'text-cyan-300'
                : 'text-zinc-300';
          return (
            <div key={idx} className={cls}>
              {line || ' '}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-2 space-y-2">
      <div className="flex flex-wrap gap-2">
        {toolSelectedMessage?.content.tool_calls &&
          toolSelectedMessage.content.tool_calls.map((toolCall: ToolCall) => {
            const actToolMessages = (actMessage?.messages.filter(m => m.type === 'agent:lifecycle:step:act:tool') || []) as (AggregatedMessage & {
              type: 'agent:lifecycle:step:act:tool';
            })[];
            const executeComplete = actToolMessages
              .flatMap(m => m.messages)
              .find(m => m.type === 'agent:lifecycle:step:act:tool:execute:complete' && m.content.id === toolCall.id);
            const resultText = String(executeComplete?.content?.result || '');
            const hasError = !!executeComplete?.content.error || /^Error:/i.test(resultText.trim());

            const { toolName, functionName } = getToolByPrefix(toolCall.function.name);

            return (
              <Badge
                key={toolCall.id}
                variant="outline"
                className="cursor-pointer gap-1 font-mono font-medium"
                onClick={() => {
                  setData({ type: 'tool', toolId: toolCall.id });
                }}
              >
                {hasError ? (
                  <TriangleAlert className="h-3.5 w-3.5 text-rose-500" />
                ) : executeComplete ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                ) : (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                )}
                {toolName} {functionName}
              </Badge>
            );
          })}
      </div>
      {toolSelectedMessage?.content.tool_calls?.length ? (
        <div className="space-y-2 rounded-md border bg-muted/20 p-2">
          {toolSelectedMessage.content.tool_calls.map((toolCall: ToolCall) => {
            const actToolMessages = (actMessage?.messages.filter(m => m.type === 'agent:lifecycle:step:act:tool') || []) as (AggregatedMessage & {
              type: 'agent:lifecycle:step:act:tool';
            })[];
            const toolEvents = actToolMessages.find(m => m.content?.id === toolCall.id)?.messages || [];
            const executeComplete = toolEvents.find(m => m.type === 'agent:lifecycle:step:act:tool:execute:complete');
            const fileUpdates = toolEvents.filter(m => m.type === 'agent:lifecycle:step:act:tool:file:updated');
            const added = fileUpdates.reduce((sum, item) => sum + Number(item.content?.added_lines || 0), 0);
            const deleted = fileUpdates.reduce((sum, item) => sum + Number(item.content?.deleted_lines || 0), 0);
            const resultText = String(executeComplete?.content?.result || '').trim();
            const hasError = !!executeComplete?.content?.error || /^Error:/i.test(resultText);
            const diffLines = (
              fileUpdates.find(m => Array.isArray(m.content?.diff_preview?.lines))?.content?.diff_preview?.lines as string[] | undefined
            ) || [];
            const shortResult = resultText
              .replace(/\s+/g, ' ')
              .slice(0, 180);
            return (
              <div key={`${toolCall.id}-summary`} className="rounded border bg-background/70 p-2">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 font-mono">
                    <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
                    {toolCall.function.name}
                  </span>
                  <span className="text-muted-foreground">
                    {executeComplete ? (hasError ? 'failed' : 'completed') : 'running'} · {fileUpdates.length} file change{fileUpdates.length === 1 ? '' : 's'}
                    {fileUpdates.length ? (
                      <>
                        {' '}
                        · <span className="text-emerald-600">+{added}</span> <span className="text-rose-600">-{deleted}</span>
                      </>
                    ) : null}
                  </span>
                </div>
                {shortResult ? (
                  <div className={`text-xs ${hasError ? 'text-rose-600' : 'text-muted-foreground'}`}>{shortResult}{resultText.length > 180 ? '…' : ''}</div>
                ) : null}
                {fileUpdates.length ? (
                  <div className="mt-1 text-xs text-muted-foreground">
                    {fileUpdates
                      .map(m => String(m.content?.path || ''))
                      .filter(Boolean)
                      .slice(0, 3)
                      .join(' · ')}
                    {fileUpdates.length > 3 ? ` · +${fileUpdates.length - 3} more` : ''}
                  </div>
                ) : null}
                {diffLines.length ? renderDiff(diffLines) : null}
              </div>
            );
          })}
        </div>
      ) : null}
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
