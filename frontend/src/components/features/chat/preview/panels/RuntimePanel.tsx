import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAsync } from '@/hooks/use-async';
import { getConversationRuntime, killConversationProcess, stopConversationContainer } from '@/services/conversations';
import { ActivityIcon, ExternalLinkIcon, LoaderIcon, StopCircleIcon } from 'lucide-react';
import { useEffect, useState } from 'react';

interface RuntimePanelProps {
  conversationId: string;
  initialTab?: 'processes' | 'ports' | 'containers';
  performanceMode?: boolean;
}

export const RuntimePanel = ({
  conversationId,
  initialTab = 'processes',
  performanceMode = false,
}: RuntimePanelProps) => {
  const [refreshTick, setRefreshTick] = useState(0);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [tab, setTab] = useState<'processes' | 'ports' | 'containers'>(initialTab);
  const { data: runtime, isLoading } = useAsync(
    async () => getConversationRuntime(conversationId),
    [],
    { deps: [conversationId, refreshTick] },
  );

  useEffect(() => {
    const interval = window.setInterval(
      () => setRefreshTick(tick => tick + 1),
      performanceMode ? 12000 : 3000,
    );
    return () => window.clearInterval(interval);
  }, [performanceMode]);

  const killProcess = async (pid: number) => {
    setBusyKey(`process:${pid}`);
    try {
      await killConversationProcess(conversationId, pid);
      setRefreshTick(tick => tick + 1);
    } finally {
      setBusyKey(null);
    }
  };

  const stopContainer = async (containerId: string) => {
    setBusyKey(`container:${containerId}`);
    try {
      await stopConversationContainer(conversationId, containerId);
      setRefreshTick(tick => tick + 1);
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="h-full min-h-0 p-4">
      <Card className="flex h-full min-h-0 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ActivityIcon className="text-primary h-5 w-5" />
              <CardTitle className="text-base">Runtime</CardTitle>
            </div>
            <Badge variant={runtime?.running_count ? 'default' : 'outline'}>
              {runtime?.running_count ? `${runtime.running_count} running` : isLoading ? 'loading' : 'idle'}
            </Badge>
          </div>
          <CardDescription>Processes and containers for this conversation computer.</CardDescription>
          <div className="mt-2 flex gap-1">
            {(['processes', 'ports', 'containers'] as const).map(item => (
              <Button
                key={item}
                size="sm"
                variant={tab === item ? 'default' : 'outline'}
                onClick={() => setTab(item)}
                className="h-7 capitalize"
              >
                {item}
              </Button>
            ))}
          </div>
        </CardHeader>

        <CardContent className="min-h-0 flex-1 space-y-4 overflow-auto">
          {/* Ports */}
          {tab === 'ports' && (
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Exposed URLs</h3>
                <span className="text-muted-foreground text-xs">{runtime?.urls?.length || 0}</span>
              </div>
              <div className="overflow-hidden rounded-md border">
                {runtime?.urls?.length ? (
                  runtime.urls.map(item => (
                    <div
                      key={`${item.pid}:${item.port}`}
                      className="grid grid-cols-[80px_1fr_auto] gap-3 border-b p-2 last:border-b-0"
                    >
                      <div className="font-mono text-xs">:{item.port}</div>
                      <div className="min-w-0">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="block truncate text-sm font-medium text-primary hover:underline"
                        >
                          {item.url}
                        </a>
                        <div className="text-muted-foreground truncate font-mono text-xs">{item.command || item.args}</div>
                      </div>
                      <Button size="sm" variant="outline" asChild title="Open URL">
                        <a href={item.url} target="_blank" rel="noreferrer">
                          <ExternalLinkIcon className="h-3.5 w-3.5" />
                        </a>
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="text-muted-foreground p-3 text-sm">
                    {isLoading ? 'Scanning ports...' : 'No listening web ports detected.'}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Processes */}
          {tab === 'processes' && (
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Processes</h3>
                <span className="text-muted-foreground text-xs">{runtime?.processes.length || 0}</span>
              </div>
              <div className="overflow-hidden rounded-md border">
                {runtime?.processes.length ? (
                  runtime.processes.map(process => (
                    <div key={process.pid} className="grid grid-cols-[72px_1fr_auto] gap-3 border-b p-2 last:border-b-0">
                      <div className="font-mono text-xs">
                        <div>{process.pid}</div>
                        <div className="text-muted-foreground">{process.elapsed}</div>
                      </div>
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <div className="truncate text-sm font-medium">{process.command}</div>
                          {process.ports?.map(port => (
                            <Badge key={port} variant="outline" className="font-mono text-[10px]">
                              :{port}
                            </Badge>
                          ))}
                          {process.zombie && (
                            <Badge variant="outline" className="font-mono text-[10px]">zombie</Badge>
                          )}
                        </div>
                        <div className="text-muted-foreground max-h-10 overflow-hidden break-all font-mono text-xs">
                          {process.args}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={process.protected || busyKey === `process:${process.pid}`}
                        onClick={() => killProcess(process.pid)}
                        title={
                          process.zombie
                            ? 'Zombie processes are already dead'
                            : process.protected
                              ? 'Protected system process'
                              : 'Kill process'
                        }
                      >
                        {busyKey === `process:${process.pid}` ? (
                          <LoaderIcon className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <StopCircleIcon className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="text-muted-foreground p-3 text-sm">
                    {isLoading ? 'Loading processes...' : 'No sandbox processes found.'}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Containers */}
          {tab === 'containers' && (
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Docker Containers</h3>
                <span className="text-muted-foreground text-xs">{runtime?.containers.length || 0}</span>
              </div>
              {runtime?.hidden_system_containers ? (
                <div className="text-muted-foreground text-xs">
                  {runtime.hidden_system_containers} OpenManus system container
                  {runtime.hidden_system_containers === 1 ? '' : 's'} hidden.
                </div>
              ) : null}
              <div className="overflow-hidden rounded-md border">
                {runtime?.containers.length ? (
                  runtime.containers.map(container => (
                    <div
                      key={container.id}
                      className="grid grid-cols-[84px_1fr_auto] gap-3 border-b p-2 last:border-b-0"
                    >
                      <div className="font-mono text-xs">
                        <div>{container.id}</div>
                        <div className="text-muted-foreground truncate">{container.status}</div>
                      </div>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">{container.name}</div>
                        <div className="text-muted-foreground truncate text-xs">{container.image}</div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={container.protected || busyKey === `container:${container.id}`}
                        onClick={() => stopContainer(container.id)}
                        title={container.protected ? 'Protected OpenManus container' : 'Stop container'}
                      >
                        {busyKey === `container:${container.id}` ? (
                          <LoaderIcon className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <StopCircleIcon className="h-3.5 w-3.5" />
                        )}
                      </Button>
                    </div>
                  ))
                ) : (
                  <div className="text-muted-foreground p-3 text-sm">
                    {isLoading ? 'Loading containers...' : 'No Docker containers found.'}
                  </div>
                )}
              </div>
            </section>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
