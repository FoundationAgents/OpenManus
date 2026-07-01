export interface Conversation {
  id: string;
  conversation_id: string;
  title: string;
  model?: string | null;
  settings?: {
    disabled_tools?: string[];
    requested_context_window?: number;
    auto_context_compress?: boolean;
    disabled_skills?: string[];
    enable_vendor_skills?: boolean;
    pinned_skills?: string[];
    identity_notes?: string;
    auto_skill_curator?: boolean;
    skill_suggestions?: Array<{
      key: string;
      tools: string[];
      count: number;
      last_seen?: number;
      last_prompt?: string;
    }>;
  };
  context?: {
    requested_window?: number | null;
    received_window?: number | null;
    received_window_source?: string | null;
    current_input_tokens?: number;
    usage_ratio?: number | null;
    is_near_limit?: boolean;
    auto_context_compress?: boolean;
  } | null;
  latest_task_id?: string | null;
  latest_status?: string | null;
  state?: 'idle' | 'running' | 'paused' | 'waiting' | 'finished' | 'error' | 'stuck';
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ConversationEvent {
  id?: string;
  type: 'progress';
  name: string;
  content: Record<string, unknown>;
  task_id?: string;
  created_at?: string | null;
}

export interface ConversationHistory {
  conversation: Conversation;
  tasks: Array<{
    id: string;
    task_id: string;
    status?: string;
    request?: string;
    conversation_id?: string;
    created_at?: string | null;
  }>;
  events: ConversationEvent[];
  pagination?: {
    limit?: number;
    next_before_event_id?: number | null;
    has_more?: boolean;
  };
}

export interface ConversationRuntime {
  conversation_id: string;
  status: 'running' | 'idle';
  running_count: number;
  hidden_system_containers?: number;
  agentmemory?: IntegrationsHealth['agentmemory'];
  sandbox?: {
    exists: boolean;
    status: string;
    container?: {
      id: string;
      name: string;
      image: string;
    } | null;
  };
  urls?: Array<{
    port: string;
    url: string;
    pid: number;
    command: string;
    args: string;
  }>;
  processes: Array<{
    pid: number;
    ppid: number;
    stat: string;
    elapsed: string;
    command: string;
    args: string;
    ports?: string[];
    zombie?: boolean;
    protected?: boolean;
  }>;
  containers: Array<{
    id: string;
    name: string;
    image: string;
    status: string;
    command: string;
    protected?: boolean;
  }>;
}

export interface SkillSummary {
  name: string;
  path: string;
  type: string;
  version: string;
  agent: string;
  triggers: string[];
  enabled?: boolean;
}

export interface ObsidianGraph {
  conversation_id: string;
  node_count: number;
  edge_count: number;
  nodes: Array<{
    id: string;
    path: string;
    title: string;
    tags?: string[];
    updated_at?: string | null;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    relation: string;
  }>;
}

export interface IntegrationsHealth {
  conversation_id: string;
  agentmemory: {
    enabled: boolean;
    available: boolean;
    live: boolean;
    reason?: string;
    base_url?: string;
    project?: string;
    conversation_hits?: number;
    vector_backend?: string;
    vector_live?: boolean;
    vector_count?: number;
    embedding_provider?: string;
    last_vector_error?: string | null;
  };
  obsidian: {
    enabled: boolean;
    available: boolean;
    live: boolean;
    reason?: string;
    note_count?: number;
  };
  llm_connection?: {
    configured: boolean;
    live: boolean;
    reason?: string;
    api_type?: string;
    base_url?: string;
    model_count?: number;
  };
}

export async function listConversations(): Promise<{ conversations: Conversation[] }> {
  const response = await fetch('/api/conversations', {
    credentials: 'same-origin',
  });
  if (!response.ok) return { conversations: [] };
  return response.json();
}

export async function createConversation(title = 'New conversation', model?: string): Promise<Conversation> {
  const response = await fetch('/api/conversations', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, model }),
  });
  if (!response.ok) throw new Error('Could not create conversation');
  return response.json();
}

export async function getConversation(conversationId: string): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${conversationId}`, {
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not load conversation');
  return response.json();
}

export async function getConversationHistory(conversationId: string, limit = 160): Promise<ConversationHistory> {
  const response = await fetch(`/api/conversations/${conversationId}/events/history?limit=${encodeURIComponent(String(limit))}`, {
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not load conversation history');
  return response.json();
}

export async function getConversationHistoryAll(conversationId: string): Promise<ConversationHistory> {
  const pageSize = 1000;
  let beforeEventId: number | null | undefined = undefined;
  let conversation: Conversation | undefined;
  let tasks: ConversationHistory['tasks'] = [];
  const events: ConversationEvent[] = [];

  for (let page = 0; page < 10; page += 1) {
    const suffix = beforeEventId ? `&before_event_id=${beforeEventId}` : '';
    const response = await fetch(
      `/api/conversations/${conversationId}/events/history?limit=${pageSize}${suffix}`,
      { credentials: 'same-origin' },
    );
    if (!response.ok) throw new Error('Could not load conversation history');
    const data: ConversationHistory = await response.json();
    conversation = data.conversation;
    tasks = data.tasks || tasks;
    events.push(...(data.events || []));
    const pagination = data.pagination || {};
    if (!pagination.has_more || !pagination.next_before_event_id) {
      break;
    }
    beforeEventId = pagination.next_before_event_id;
  }

  return {
    conversation: conversation as Conversation,
    tasks,
    events,
  };
}

export async function getConversationRuntime(conversationId: string): Promise<ConversationRuntime> {
  const response = await fetch(`/api/conversations/${conversationId}/runtime`, {
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not load conversation runtime');
  return response.json();
}

export async function killConversationProcess(conversationId: string, pid: number): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}/runtime/processes/${pid}/kill`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal: 'TERM' }),
  });
  if (!response.ok) throw new Error('Could not kill process');
}

export async function stopConversationContainer(conversationId: string, containerId: string): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}/runtime/containers/${containerId}/stop`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not stop container');
}

export async function pauseConversationSandbox(conversationId: string): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}/sandbox/pause`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not pause sandbox');
}

export async function resumeConversationSandbox(conversationId: string): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}/sandbox/resume`, {
    method: 'POST',
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not resume sandbox');
}

export async function listSkills(conversationId?: string): Promise<{ skills: SkillSummary[] }> {
  const suffix = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : '';
  const response = await fetch(`/api/skills${suffix}`, {
    credentials: 'same-origin',
  });
  if (!response.ok) return { skills: [] };
  return response.json();
}

export async function getObsidianGraph(conversationId: string): Promise<ObsidianGraph> {
  const response = await fetch(`/api/conversations/${conversationId}/obsidian/graph`, {
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not load vault graph');
  return response.json();
}

export async function getIntegrationsHealth(conversationId: string): Promise<IntegrationsHealth> {
  const response = await fetch(`/api/conversations/${conversationId}/integrations/health`, {
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not load integrations health');
  return response.json();
}

export async function sendConversationMessage(
  conversationId: string,
  message: string,
  model?: string,
): Promise<{ conversation_id: string; task_id: string; queued: boolean; created_task: boolean }> {
  const response = await fetch(`/api/conversations/${conversationId}/messages`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Could not send message');
  }
  return response.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetch(`/api/conversations/${conversationId}`, {
    method: 'DELETE',
    credentials: 'same-origin',
  });
  if (!response.ok) throw new Error('Could not delete conversation');
}

export async function updateConversationSettings(
  conversationId: string,
  settings: {
    model?: string;
    disabled_tools?: string[];
    requested_context_window?: number | null;
    auto_context_compress?: boolean;
    disabled_skills?: string[];
    enable_vendor_skills?: boolean;
    pinned_skills?: string[];
    identity_notes?: string;
    auto_skill_curator?: boolean;
  },
): Promise<Conversation> {
  const response = await fetch(`/api/conversations/${conversationId}/settings`, {
    method: 'PUT',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!response.ok) throw new Error('Could not update conversation settings');
  return response.json();
}
