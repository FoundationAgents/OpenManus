import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { Message } from '@/libs/chat-messages/types';
import { LoaderIcon, SquareTerminalIcon } from 'lucide-react';

// ---------------------------------------------------------------------------
// Live Activity — shows the event stream in reverse chronological order
// ---------------------------------------------------------------------------

export const LiveActivityPanel = ({ messages }: { messages: Message[] }) => {
  const recent = [...messages]
    .filter(
      message =>
        Boolean(message.type) &&
        message.type !== 'agent:lifecycle:step:act:tool:terminal:output',
    )
    .slice(-24)
    .reverse();

  const terminalTail = messages
    .filter(message => message.type === 'agent:lifecycle:step:act:tool:terminal:output')
    .map(message => String(message.content.chunk || ''))
    .join('')
    .slice(-5000);

  const status = recent.find(message => message.type === 'agent:lifecycle:complete')
    ? 'Completed'
    : recent.find(message => message.type === 'agent:lifecycle:terminated')
      ? 'Terminated'
      : recent.find(message => message.type === 'agent:lifecycle:step:error')
        ? 'Error'
        : 'Running';

  return (
    <div className="h-full min-h-0 p-4">
      <Card className="flex h-full min-h-0 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Live Activity</CardTitle>
            <Badge
              variant={
                status === 'Running' ? 'default' : status === 'Completed' ? 'outline' : 'destructive'
              }
            >
              {status}
            </Badge>
          </div>
          <CardDescription>What the agent is doing right now.</CardDescription>
        </CardHeader>
        <CardContent className="grid min-h-0 flex-1 grid-rows-[1fr_auto] gap-3 overflow-hidden">
          <div className="min-h-0 overflow-auto rounded-md border">
            {recent.length ? (
              recent.map((message, index) => (
                <div key={message.index || index} className="border-b p-2 last:border-b-0">
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-xs font-medium">{String(message.type || 'event')}</div>
                    <div className="text-muted-foreground text-[11px]">
                      {message.createdAt ? new Date(message.createdAt).toLocaleTimeString() : ''}
                    </div>
                  </div>
                  {message.content?.name ? (
                    <div className="text-muted-foreground mt-0.5 truncate font-mono text-[11px]">
                      {String(message.content.name)}
                    </div>
                  ) : null}
                  {message.content?.message ? (
                    <div className="mt-1 text-xs">{String(message.content.message)}</div>
                  ) : null}
                </div>
              ))
            ) : (
              <div className="text-muted-foreground p-3 text-sm">No live events yet.</div>
            )}
          </div>
          {/* Terminal tail */}
          <div className="overflow-hidden rounded-md border bg-neutral-950 text-neutral-100">
            <div className="border-b border-neutral-800 px-3 py-1.5 text-xs font-medium">Terminal tail</div>
            <pre className="max-h-36 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-[11px] leading-5">
              {terminalTail || 'No terminal output yet.'}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Terminal output — full scrollable terminal log
// ---------------------------------------------------------------------------

export const TerminalOutputPanel = ({ messages }: { messages: Message[] }) => {
  const output = messages
    .filter(message => message.type === 'agent:lifecycle:step:act:tool:terminal:output')
    .map(message => {
      const stream = message.content.stream === 'stderr' ? 'stderr' : 'stdout';
      return `[${message.content.name || 'terminal'}:${stream}] ${message.content.chunk || ''}`;
    })
    .join('');

  return (
    <div className="h-full min-h-0 p-4">
      <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-md border bg-neutral-950 text-neutral-100">
        <div className="flex items-center gap-2 border-b border-neutral-800 px-3 py-2 text-sm font-medium">
          <SquareTerminalIcon className="h-4 w-4" />
          Terminal
        </div>
        <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-5">
          {output || 'No terminal output yet.'}
        </pre>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Tool execution card
// ---------------------------------------------------------------------------

export const ToolPanel = ({
  name,
  toolId,
  args,
  result,
  liveOutput,
  isExecuting,
}: {
  name?: string;
  toolId?: string;
  args?: unknown;
  result?: unknown;
  liveOutput?: string;
  isExecuting: boolean;
}) => {
  const isTerminalTool = name === 'python_execute' || name === 'bash';
  const parsedArgs = _normalizeArgs(args);
  const terminalInput = _getTerminalInput(name, parsedArgs);

  return (
    <div className="h-full min-h-0 p-4">
      <Card className="flex h-full min-h-0 flex-col overflow-hidden">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SquareTerminalIcon className={`h-5 w-5 ${isTerminalTool ? 'text-primary' : 'text-muted-foreground'}`} />
              <CardTitle className="text-base">{isTerminalTool ? 'Terminal' : 'Tool Execution'}</CardTitle>
            </div>
            {isExecuting && (
              <div className="flex items-center gap-1 text-amber-500">
                <LoaderIcon className="h-4 w-4 animate-spin" />
                <span className="text-xs font-medium">Running…</span>
              </div>
            )}
          </div>
          {toolId && (
            <CardDescription className="font-mono text-xs">ID: {toolId}</CardDescription>
          )}
        </CardHeader>
        <CardContent className="min-h-0 flex-1 space-y-4 overflow-auto">
          {name && (
            <div className="space-y-1">
              <div className="text-muted-foreground text-xs font-medium">Tool</div>
              <code className="rounded border bg-muted/40 px-2 py-0.5 text-xs">{name}</code>
            </div>
          )}
          {isTerminalTool ? (
            <_TerminalBlock
              command={name}
              input={terminalInput}
              output={_formatTerminalOutput(result)}
              liveOutput={liveOutput}
              isExecuting={isExecuting}
            />
          ) : (
            <>
              {_hasArgs(parsedArgs) && (
                <div className="space-y-1">
                  <div className="text-muted-foreground text-xs font-medium">Parameters</div>
                  <_CodeBlock value={_formatArgs(parsedArgs)} language="json" maxHeight="18rem" />
                </div>
              )}
              {result ? (
                <div className="space-y-1">
                  <div className="text-muted-foreground text-xs font-medium">Result</div>
                  <_CodeBlock value={String(result)} language="text" maxHeight="24rem" />
                </div>
              ) : (
                isExecuting && <_ProcessingSpinner />
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

import SyntaxHighlighter from 'react-syntax-highlighter';
import { githubGist } from 'react-syntax-highlighter/dist/esm/styles/hljs';

const _normalizeArgs = (args: unknown): unknown => {
  if (typeof args !== 'string') return args;
  try { return JSON.parse(args); } catch { return args; }
};

const _hasArgs = (args: unknown): boolean => {
  if (!args) return false;
  if (typeof args === 'string') return args.trim().length > 0;
  if (typeof args === 'object') return Object.keys(args as object).length > 0;
  return true;
};

const _formatArgs = (args: unknown): string =>
  typeof args === 'string' ? args : JSON.stringify(args, null, 2);

const _getTerminalInput = (name: string | undefined, args: unknown): string => {
  if (!args || typeof args !== 'object') return '';
  const r = args as Record<string, unknown>;
  if (name === 'python_execute') return String(r.code || '');
  if (name === 'bash') return String(r.command || '');
  return _formatArgs(args);
};

const _formatTerminalOutput = (output: unknown): string => {
  if (!output) return '';
  if (typeof output !== 'string') return JSON.stringify(output, null, 2);
  const match = output.match(/Observed output of cmd `[^`]+` executed:\n([\s\S]*)$/);
  if (match?.[1]) return match[1];
  return output;
};

const _CodeBlock = ({ value, language, maxHeight }: { value: string; language: string; maxHeight: string }) => (
  <div className="overflow-auto rounded-md border bg-muted/40" style={{ maxHeight }}>
    <SyntaxHighlighter
      language={language}
      showLineNumbers
      wrapLongLines
      style={githubGist}
      customStyle={{
        color: 'inherit',
        backgroundColor: 'inherit',
        fontSize: '0.8125rem',
        lineHeight: '1.5',
        margin: 0,
        borderRadius: 0,
        whiteSpace: 'pre-wrap',
        overflowWrap: 'anywhere',
      }}
    >
      {value}
    </SyntaxHighlighter>
  </div>
);

const _TerminalBlock = ({
  command,
  input,
  output,
  liveOutput,
  isExecuting,
}: {
  command?: string;
  input: string;
  output?: string;
  liveOutput?: string;
  isExecuting: boolean;
}) => {
  const visible = liveOutput || output || '';
  return (
    <div className="overflow-hidden rounded-md border bg-neutral-950 text-neutral-100">
      <div className="flex items-center justify-between border-b border-neutral-800 px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-medium">
          <SquareTerminalIcon className="h-3.5 w-3.5" />
          <span>{command === 'python_execute' ? 'python' : command || 'terminal'}</span>
        </div>
        {isExecuting && (
          <div className="flex items-center gap-1 text-xs text-amber-300">
            <LoaderIcon className="h-3.5 w-3.5 animate-spin" />
            running
          </div>
        )}
      </div>
      <div className="max-h-[34rem] overflow-auto p-3 font-mono text-xs leading-5">
        {input && (
          <pre className="mb-3 whitespace-pre text-emerald-300">
            <span className="text-neutral-500">$ </span>
            {input}
          </pre>
        )}
        {visible ? (
          <pre className="whitespace-pre text-neutral-100">{visible}</pre>
        ) : (
          <div className="text-neutral-500">Waiting for output…</div>
        )}
      </div>
    </div>
  );
};

const _ProcessingSpinner = () => (
  <div className="bg-muted/20 flex items-center justify-center rounded-md border p-6">
    <div className="text-muted-foreground flex flex-col items-center gap-2">
      <LoaderIcon className="h-5 w-5 animate-spin" />
      <span className="text-sm">Processing…</span>
    </div>
  </div>
);
