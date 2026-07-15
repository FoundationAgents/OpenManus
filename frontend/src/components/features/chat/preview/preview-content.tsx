/**
 * PreviewContent — thin router that delegates to focused panel components.
 *
 * This file used to be 1,087 lines containing all panel logic inline.
 * It is now ~120 lines. Each panel lives in ./panels/ and can be edited,
 * tested, and lazy-loaded independently.
 */
import type { Message } from '@/libs/chat-messages/types';
import { useAsync } from '@/hooks/use-async';
import { listSkills } from '@/services/conversations';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { usePreviewData } from './store';
import { BrowserPanel } from './panels/BrowserPanel';
import { RuntimePanel } from './panels/RuntimePanel';
import { LiveActivityPanel, TerminalOutputPanel, ToolPanel } from './panels/ToolsPanel';
import { WorkspacePanel, ChangesPanel } from './panels/WorkspacePanel';
import { VaultPanel } from './panels/VaultPanel';

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

export const PreviewContent = ({
  messages,
  performanceMode = false,
}: {
  messages: Message[];
  performanceMode?: boolean;
}) => {
  const { data } = usePreviewData();

  // Tool execution detail
  if (data?.type === 'tool') {
    const start = messages.find(
      m => m.type === 'agent:lifecycle:step:act:tool:execute:start' && m.content.id === data.toolId,
    );
    const complete = messages.find(
      m => m.type === 'agent:lifecycle:step:act:tool:execute:complete' && m.content.id === data.toolId,
    );
    const liveOutput = messages
      .filter(m => m.type === 'agent:lifecycle:step:act:tool:terminal:output' && m.content.id === data.toolId)
      .map(m => m.content.chunk)
      .join('');

    return (
      <ToolPanel
        name={start?.content.name}
        toolId={data.toolId}
        args={start?.content.arguments ?? start?.content.args}
        result={complete?.content.result}
        liveOutput={liveOutput}
        isExecuting={Boolean(start && !complete)}
      />
    );
  }

  if (data?.type === 'browser') {
    return (
      <BrowserPanel url={data.url} title={data.title} screenshot={data.screenshot} />
    );
  }

  if (data?.type === 'workspace') {
    return <WorkspacePanel />;
  }

  if (data?.type === 'live') {
    return <LiveActivityPanel messages={messages} />;
  }

  if (data?.type === 'runtime') {
    return (
      <RuntimePanel
        conversationId={data.conversationId}
        initialTab={data.tab}
        performanceMode={performanceMode}
      />
    );
  }

  if (data?.type === 'terminal') {
    return <TerminalOutputPanel messages={messages} />;
  }

  if (data?.type === 'changes') {
    return <ChangesPanel messages={messages} />;
  }

  if (data?.type === 'skills') {
    return <SkillsPanel conversationId={data.conversationId} />;
  }

  if (data?.type === 'vault') {
    return <VaultPanel conversationId={data.conversationId} />;
  }

  // Default: live activity feed
  return <LiveActivityPanel messages={messages} />;
};

// ---------------------------------------------------------------------------
// Skills panel (small enough to keep here inline)
// ---------------------------------------------------------------------------

const SkillsPanel = ({ conversationId }: { conversationId?: string }) => {
  const { data: skills, isLoading } = useAsync(async () => listSkills(conversationId), [], {
    deps: [conversationId],
  });
  return (
    <div className="h-full min-h-0 p-4">
      <Card className="flex h-full min-h-0 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Skills</CardTitle>
          <CardDescription>OpenHands-style skills available to this conversation.</CardDescription>
        </CardHeader>
        <CardContent className="min-h-0 flex-1 overflow-auto">
          {isLoading ? (
            <div className="text-muted-foreground text-sm">Loading skills…</div>
          ) : skills?.skills.length ? (
            <div className="space-y-2">
              {skills.skills.map(skill => (
                <div key={skill.path} className="rounded-md border p-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium">{skill.name}</div>
                    <Badge variant="outline">{skill.type}</Badge>
                  </div>
                  <div className="text-muted-foreground mt-1 truncate font-mono text-xs">{skill.path}</div>
                  {skill.triggers.length ? (
                    <div className="text-muted-foreground mt-1 text-xs">
                      Triggers: {skill.triggers.join(', ')}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-muted-foreground text-sm">No skills found.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
