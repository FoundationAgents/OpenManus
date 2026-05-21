import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Message } from '@/libs/chat-messages/types';
import { cn } from '@/libs/utils';
import { getConversationRuntime, pauseConversationSandbox, resumeConversationSandbox, type ConversationRuntime } from '@/services/conversations';
import type { IntegrationsHealth } from '@/services/conversations';
import { ActivityIcon, BookOpenIcon, FileClockIcon, FolderIcon, GlobeIcon, ListChecksIcon, NetworkIcon, PauseIcon, PlayIcon, SquareTerminalIcon } from 'lucide-react';
import { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { PreviewDescription } from './preview-description';
import { usePreviewData } from './store';


interface ChatPreviewProps {
  messages: Message[];
  taskId: string;
  conversationId?: string;
  integrationsHealth?: IntegrationsHealth | null;
  className?: string;
  performanceMode?: boolean;
  pollRuntime?: boolean;
}

const PreviewContent = lazy(() =>
  import('./preview-content').then(mod => ({ default: mod.PreviewContent })),
);

export const ChatPreview = ({
  messages,
  taskId,
  conversationId,
  integrationsHealth,
  className,
  performanceMode = false,
  pollRuntime = false,
}: ChatPreviewProps) => {
  const { setData } = usePreviewData();
  const [runtime, setRuntime] = useState<ConversationRuntime | null>(null);
  const runtimeDigestRef = useRef('');
  const workspacePath = `conversations/${conversationId || taskId}`;

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    const runtimeDigest = (value: ConversationRuntime | null) =>
      value
        ? JSON.stringify({
            status: value.status,
            running_count: value.running_count,
            sandbox_status: value.sandbox?.status,
            process_count: value.processes?.length || 0,
            container_count: value.containers?.length || 0,
            url_count: value.urls?.length || 0,
          })
        : '';
    runtimeDigestRef.current = '';
    const loadRuntime = async () => {
      try {
        const nextRuntime = await getConversationRuntime(conversationId);
        if (!cancelled) {
          const nextDigest = runtimeDigest(nextRuntime);
          if (nextDigest !== runtimeDigestRef.current) {
            runtimeDigestRef.current = nextDigest;
            setRuntime(nextRuntime);
          }
        }
      } catch {
        if (!cancelled) setRuntime(null);
      }
    };
    if (!pollRuntime) {
      return () => {
        cancelled = true;
      };
    }
    loadRuntime();
    if (performanceMode) {
      return () => {
        cancelled = true;
      };
    }
    const interval = window.setInterval(() => {
      if (!document.hidden) loadRuntime();
    }, 12000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [conversationId, performanceMode, pollRuntime]);

  return (
    <Card className={cn('flex h-full w-full flex-col gap-0 px-2', className)}>
      <CardHeader className="flex-none p-2 py-1">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-2">
            <CardTitle className="text-normal">Manus's Computer</CardTitle>
            {runtime && (
              <button
                className={cn(
                  'rounded-full border px-2 py-0.5 text-xs',
                  runtime.running_count > 0 ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700' : 'text-muted-foreground',
                )}
                onClick={() => conversationId && setData({ type: 'runtime', conversationId, tab: 'processes' })}
                title="Runtime processes"
              >
                {runtime.running_count > 0 ? `${runtime.running_count} running` : 'idle'}
              </button>
            )}
            {integrationsHealth && (
              <div className="hidden items-center gap-1.5 md:flex">
                <span className="rounded border px-1.5 py-0.5 text-[10px]">
                  Memory:{' '}
                  <span className={integrationsHealth.agentmemory?.live ? 'text-emerald-500' : 'text-amber-500'}>
                    {integrationsHealth.agentmemory?.live ? 'Live' : 'Down'}
                  </span>
                </span>
                <span className="rounded border px-1.5 py-0.5 text-[10px]">
                  Obsidian:{' '}
                  <span className={integrationsHealth.obsidian?.live ? 'text-emerald-500' : 'text-amber-500'}>
                    {integrationsHealth.obsidian?.live ? 'Live' : 'Waiting'}
                  </span>
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {conversationId && (
              <>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'runtime', conversationId, tab: 'processes' })} title="Processes">
                  <ActivityIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'live' })} title="Live activity">
                  <ListChecksIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'runtime', conversationId, tab: 'ports' })} title="Ports and URLs">
                  <GlobeIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'terminal' })} title="Terminal">
                  <SquareTerminalIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'changes' })} title="Changes">
                  <FileClockIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'skills', conversationId })} title="Skills">
                  <BookOpenIcon className="h-3.5 w-3.5" />
                </Button>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setData({ type: 'vault', conversationId })} title="Vault Sync">
                  <NetworkIcon className="h-3.5 w-3.5" />
                </Button>

                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={async () => {
                    if (runtime?.sandbox?.status === 'paused') await resumeConversationSandbox(conversationId);
                    else await pauseConversationSandbox(conversationId);
                    setRuntime(await getConversationRuntime(conversationId));
                  }}
                  title={runtime?.sandbox?.status === 'paused' ? 'Resume computer' : 'Pause computer'}
                >
                  {runtime?.sandbox?.status === 'paused' ? <PlayIcon className="h-3.5 w-3.5" /> : <PauseIcon className="h-3.5 w-3.5" />}
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 hover:bg-accent/80"
              onClick={() => setData({ type: 'workspace', path: workspacePath })}
              title="Workspace"
            >
              <FolderIcon className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        <PreviewDescription messages={messages} />
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-2">
        <Suspense fallback={<div className="text-xs text-muted-foreground p-3">Loading preview...</div>}>
          <PreviewContent messages={messages} performanceMode={performanceMode} />
        </Suspense>
      </CardContent>
    </Card>
  );
};
