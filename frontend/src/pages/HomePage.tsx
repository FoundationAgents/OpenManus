import { createTask } from '@/services/tasks';
import { ChatInput } from '@/components/features/chat/input';
import { useConversations } from '@/hooks/use-conversations';
import { useRecentTasks } from '@/hooks/use-tasks';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CodeIcon, GlobeIcon, FileTextIcon, SearchIcon, BrainIcon, MessageSquareIcon, ClockIcon } from 'lucide-react';

const SUGGESTED_PROMPTS = [
  { icon: CodeIcon,        label: 'Write code',    prompt: 'Write a Python script that reads a CSV file and outputs a summary report.' },
  { icon: GlobeIcon,       label: 'Browse web',    prompt: 'Search the web for the latest AI research papers published this week.' },
  { icon: FileTextIcon,    label: 'Edit files',    prompt: 'Refactor my codebase to add proper error handling and logging throughout.' },
  { icon: SearchIcon,      label: 'Research',      prompt: 'Research and summarize the key differences between React 18 and React 19.' },
  { icon: BrainIcon,       label: 'Plan a project',prompt: 'Create a detailed project plan for building a REST API with FastAPI and PostgreSQL.' },
  { icon: MessageSquareIcon, label: 'Explain code', prompt: 'Explain how this codebase works and identify potential improvements.' },
];

const CAPABILITIES = [
  { label: '💻 Code', title: 'Write, edit, and debug code' },
  { label: '🌐 Browse', title: 'Search and browse the web' },
  { label: '📁 Files', title: 'Read and edit files' },
  { label: '🔍 Search', title: 'Search codebases and docs' },
  { label: '🧠 Plan', title: 'Break down complex tasks' },
  { label: '⚙️ Run', title: 'Execute scripts and commands' },
];

export default function HomePage({ selectedModel }: { selectedModel?: string }) {
  const navigate = useNavigate();
  const params = useParams();
  const [isLoading, setIsLoading] = useState(false);
  const [draftPrompt, setDraftPrompt] = useState('');
  const abortControllerRef = useRef<AbortController | null>(null);
  const { refreshTasks } = useRecentTasks();
  const { activeConversationId, ensureConversation, refreshConversations, setActiveConversationId } = useConversations();

  useEffect(() => {
    if (params.conversationId) setActiveConversationId(params.conversationId);
  }, [params.conversationId, setActiveConversationId]);

  useEffect(() => {
    return () => { abortControllerRef.current?.abort(); };
  }, []);

  const handleSubmit = async (input: { prompt: string }) => {
    if (!input || isLoading) return;
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    try {
      const conversationId = params.conversationId || activeConversationId || (await ensureConversation());
      const res = await createTask({ prompt: input.prompt, conversationId, model: selectedModel });
      if (res.error || !res.data) throw new Error('Failed to create task');
      await refreshTasks();
      await refreshConversations();
      navigate(`/conversations/${res.data.conversation_id || conversationId}`);
    } catch (error: any) {
      if (error.name === 'AbortError') return;
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Main content area */}
      <div className="flex flex-1 flex-col items-center justify-center gap-8 overflow-y-auto px-4 py-12">

        {/* Logo + tagline */}
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border bg-background shadow-sm">
            <span className="text-3xl">🤖</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">OpenManus</h1>
          <p className="text-sm text-muted-foreground max-w-xs">
            An autonomous AI agent that codes, browses, and reasons — no fortress, purely open ground.
          </p>
        </div>

        {/* Capability chips */}
        <div className="flex flex-wrap justify-center gap-2">
          {CAPABILITIES.map(cap => (
            <span
              key={cap.label}
              title={cap.title}
              className="rounded-full border bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground hover:bg-muted/70 cursor-default transition-colors"
            >
              {cap.label}
            </span>
          ))}
        </div>

        {/* Suggested prompts */}
        <div className="grid w-full max-w-2xl grid-cols-2 gap-2 sm:grid-cols-3">
          {SUGGESTED_PROMPTS.map(({ icon: Icon, label, prompt }) => (
            <button
              key={label}
              onClick={() => setDraftPrompt(prompt)}
              className="group flex flex-col gap-1.5 rounded-xl border bg-card p-3 text-left transition-all hover:border-primary/40 hover:bg-accent/40 hover:shadow-sm active:scale-[0.98]"
            >
              <div className="flex items-center gap-2">
                <Icon className="h-3.5 w-3.5 text-primary opacity-70 group-hover:opacity-100" />
                <span className="text-xs font-semibold">{label}</span>
              </div>
              <span className="line-clamp-2 text-[11px] text-muted-foreground leading-relaxed">
                {prompt}
              </span>
            </button>
          ))}
        </div>

        {/* Recent conversations quick-resume */}
        <RecentConversations />
      </div>


      {/* Chat input pinned at bottom */}
      <ChatInput
        onSubmit={handleSubmit}
        status={isLoading ? 'thinking' : 'idle'}
        defaultValue={draftPrompt}
        key={draftPrompt} /* remount to inject the draft */
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent Conversations quick-resume
// ---------------------------------------------------------------------------

function RecentConversations() {
  const navigate = useNavigate();
  const { conversations } = useConversations();

  const recent = conversations.slice(0, 3);
  if (!recent.length) return null;

  return (
    <div className="w-full max-w-2xl space-y-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ClockIcon className="h-3 w-3" />
        Recent conversations
      </div>
      <div className="grid gap-1.5">
        {recent.map(conv => (
          <button
            key={conv.id}
            onClick={() => navigate(`/conversations/${conv.id}`)}
            className="group flex items-center gap-3 rounded-lg border bg-card px-3 py-2 text-left transition-all hover:border-primary/30 hover:bg-accent/30 active:scale-[0.99]"
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium">
                {conv.title || conv.id}
              </div>
              {conv.updated_at && (
                <div className="text-[10px] text-muted-foreground">
                  {new Date(conv.updated_at).toLocaleString()}
                </div>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              Resume →
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
