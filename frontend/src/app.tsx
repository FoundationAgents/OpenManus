import { ConfirmDialog } from '@/components/block/confirm';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { useConversations } from '@/hooks/use-conversations';
import { cn } from '@/libs/utils';
import AdminPage from '@/pages/AdminPage';
import AuthPage from '@/pages/AuthPage';
import ConversationSettingsPage from '@/pages/ConversationSettingsPage';
import HomePage from '@/pages/HomePage';
import TaskDetailPage from '@/pages/TaskDetailPage';
import { getMe, logout, type User } from '@/services/auth';
import { deleteConversation, updateConversationSettings } from '@/services/conversations';
import { ejectModel, listModels, loadModel, queryModels, type ModelOption } from '@/services/models';
import {
  HomeIcon,
  LoaderCircle,
  LoaderIcon,
  LogOut,
  MessageSquare,
  Plus,
  PowerOff,
  Settings,
  Shield,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { SidebarProvider } from './components/ui/sidebar';

type ConnectionStyle = 'lm-studio' | 'ollama' | 'openai' | 'custom';

type ConnectionProfile = {
  id: string;
  name: string;
  host: string;
  apiKey: string;
  style: ConnectionStyle;
  chatPath: string;
  modelsPath: string;
  loadPath: string;
  unloadPath: string;
  defaultModel: string;
  defaultContextWindow: string;
};

const DEFAULT_PROFILE: ConnectionProfile = {
  id: 'default',
  name: 'Default',
  host: 'http://127.0.0.1:1234',
  apiKey: '',
  style: 'lm-studio',
  chatPath: '',
  modelsPath: '',
  loadPath: '',
  unloadPath: '',
  defaultModel: '',
  defaultContextWindow: '',
};

const STORAGE = {
  selectedModel: 'openmanus.selectedModel',
  connectionProfiles: 'openmanus.connection.profiles',
  activeProfileId: 'openmanus.connection.activeProfileId',
};

function styleDefaultHost(style: ConnectionStyle): string {
  if (style === 'lm-studio') return 'http://127.0.0.1:1234';
  if (style === 'ollama') return 'http://127.0.0.1:11434';
  if (style === 'openai') return 'https://api.openai.com/v1';
  return '';
}

function matchesStyle(style: ConnectionStyle, apiType: string): boolean {
  const normalized = String(apiType || '').toLowerCase();
  if (style === 'lm-studio') return normalized === 'lmstudio' || normalized === 'lm-studio';
  if (style === 'ollama') return normalized === 'ollama';
  if (style === 'openai') return normalized === 'openai';
  // For custom connections, do not hide provider-specific models.
  return true;
}

function loadProfilesFromStorage(): ConnectionProfile[] {
  try {
    const raw = localStorage.getItem(STORAGE.connectionProfiles);
    if (!raw) return [DEFAULT_PROFILE];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || !parsed.length) return [DEFAULT_PROFILE];
    return parsed;
  } catch {
    return [DEFAULT_PROFILE];
  }
}

function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState(
    localStorage.getItem(STORAGE.selectedModel) || '',
  );
  const [isEjectingModel, setIsEjectingModel] = useState(false);
  const [isLoadingModel, setIsLoadingModel] = useState(false);
  const [requestedContextWindow, setRequestedContextWindow] = useState('');

  const [profiles, setProfiles] = useState<ConnectionProfile[]>(() =>
    typeof window !== 'undefined' ? loadProfilesFromStorage() : [DEFAULT_PROFILE],
  );
  const [activeProfileId, setActiveProfileId] = useState(
    localStorage.getItem(STORAGE.activeProfileId) || 'default',
  );
  const [pendingProfileId, setPendingProfileId] = useState(
    localStorage.getItem(STORAGE.activeProfileId) || 'default',
  );
  const [newProfileName, setNewProfileName] = useState('');
  const [showProfileOptions, setShowProfileOptions] = useState(false);
  const [profileOptionsMode, setProfileOptionsMode] = useState<'create' | 'edit'>('edit');

  const [isConnectionSettingsOpen, setIsConnectionSettingsOpen] = useState(false);
  const [connectionHostDraft, setConnectionHostDraft] = useState(DEFAULT_PROFILE.host);
  const [connectionApiKeyDraft, setConnectionApiKeyDraft] = useState(DEFAULT_PROFILE.apiKey);
  const [connectionStyleDraft, setConnectionStyleDraft] = useState<ConnectionStyle>('lm-studio');
  const [connectionChatPathDraft, setConnectionChatPathDraft] = useState('');
  const [connectionModelsPathDraft, setConnectionModelsPathDraft] = useState('');
  const [connectionLoadPathDraft, setConnectionLoadPathDraft] = useState('');
  const [connectionUnloadPathDraft, setConnectionUnloadPathDraft] = useState('');
  const [defaultModelDraft, setDefaultModelDraft] = useState('');
  const [defaultContextWindowDraft, setDefaultContextWindowDraft] = useState('');
  const [isVerifyingConnection, setIsVerifyingConnection] = useState(false);

  const {
    conversations,
    activeConversationId,
    createNewConversation,
    refreshConversations,
    removeConversation,
    setActiveConversationId,
  } = useConversations();
  const location = useLocation();
  const navigate = useNavigate();

  const activeProfile =
    profiles.find(profile => profile.id === activeProfileId) || profiles[0] || DEFAULT_PROFILE;
  const currentTaskId = location.pathname.startsWith('/tasks/')
    ? location.pathname.split('/').pop()
    : undefined;

  const filteredModels = useMemo(
    () => models.filter(model => matchesStyle(connectionStyleDraft, model.api_type)),
    [models, connectionStyleDraft],
  );

  const groupedFilteredModels = useMemo(() => {
    const groups = new Map<string, ModelOption[]>();
    for (const model of filteredModels) {
      const base = String(model.base_model || model.id || 'model');
      const bucket = groups.get(base) || [];
      bucket.push(model);
      groups.set(base, bucket);
    }
    return [...groups.entries()];
  }, [filteredModels]);

  const selectedModelInfo = useMemo(
    () => filteredModels.find(model => model.id === selectedModel),
    [filteredModels, selectedModel],
  );
  const selectedModelState = String(selectedModelInfo?.state || '').toLowerCase();
  const selectedModelLoaded =
    selectedModelState === 'loaded' || selectedModelState === 'running';

  const styleEndpoints = useMemo(() => {
    if (connectionStyleDraft === 'lm-studio') {
      return {
        chat: '/v1/chat/completions',
        models: '/v1/models',
        load: '/api/v1/models/load',
        unload: '/api/v1/models/unload',
      };
    }
    if (connectionStyleDraft === 'ollama') {
      return {
        chat: '/v1/chat/completions',
        models: '/v1/models',
        load: '/api/tags',
        unload: '/api/ps',
      };
    }
    if (connectionStyleDraft === 'openai') {
      return {
        chat: '/v1/chat/completions',
        models: '/v1/models',
        load: '(n/a)',
        unload: '(n/a)',
      };
    }
    return {
      chat: connectionChatPathDraft || '/v1/chat/completions',
      models: connectionModelsPathDraft || '/v1/models',
      load: connectionLoadPathDraft || '/api/v1/models/load',
      unload: connectionUnloadPathDraft || '/api/v1/models/unload',
    };
  }, [
    connectionStyleDraft,
    connectionChatPathDraft,
    connectionModelsPathDraft,
    connectionLoadPathDraft,
    connectionUnloadPathDraft,
  ]);

  const fetchModelsForProfile = async (profile: ConnectionProfile): Promise<ModelOption[]> => {
    try {
      const items = await queryModels({
        host: profile.host || styleDefaultHost(profile.style),
        api_key: profile.apiKey || '',
        style: profile.style,
        models_path: profile.modelsPath || '',
      });
      if (items.length) return items;
    } catch {
      // fallback below
    }
    return listModels();
  };

  useEffect(() => {
    localStorage.setItem(STORAGE.connectionProfiles, JSON.stringify(profiles));
  }, [profiles]);

  useEffect(() => {
    localStorage.setItem(STORAGE.activeProfileId, activeProfileId);
  }, [activeProfileId]);

  useEffect(() => {
    setPendingProfileId(activeProfileId);
  }, [activeProfileId]);

  useEffect(() => {
    getMe().then(res => setUser(res.user || null));
  }, []);

  useEffect(() => {
    if (!user) return;
    refreshConversations();
    fetchModelsForProfile(activeProfile).then(items => {
      setModels(items);
      const initial = selectedModel || activeProfile.defaultModel;
      if (initial && items.some(model => model.id === initial)) {
        setSelectedModel(initial);
        localStorage.setItem(STORAGE.selectedModel, initial);
      } else if (items[0]?.id) {
        setSelectedModel(items[0].id);
        localStorage.setItem(STORAGE.selectedModel, items[0].id);
      }
    });
  }, [user, refreshConversations, activeProfile, activeProfile.defaultModel, selectedModel]);

  useEffect(() => {
    setConnectionHostDraft(activeProfile.host || styleDefaultHost(activeProfile.style));
    setConnectionApiKeyDraft(activeProfile.apiKey || '');
    setConnectionStyleDraft(activeProfile.style || 'lm-studio');
    setConnectionChatPathDraft(activeProfile.chatPath || '');
    setConnectionModelsPathDraft(activeProfile.modelsPath || '');
    setConnectionLoadPathDraft(activeProfile.loadPath || '');
    setConnectionUnloadPathDraft(activeProfile.unloadPath || '');
    setDefaultModelDraft(activeProfile.defaultModel || '');
    setDefaultContextWindowDraft(activeProfile.defaultContextWindow || '');
  }, [activeProfileId, activeProfile]);

  useEffect(() => {
    if (!filteredModels.length) return;
    if (!selectedModel || !filteredModels.some(model => model.id === selectedModel)) {
      setSelectedModel(filteredModels[0].id);
      localStorage.setItem(STORAGE.selectedModel, filteredModels[0].id);
    }
  }, [filteredModels, selectedModel]);

  useEffect(() => {
    const activeConversation = conversations.find(item => item.id === activeConversationId);
    const value = activeConversation?.settings?.requested_context_window;
    setRequestedContextWindow(value ? String(value) : activeProfile.defaultContextWindow || '');
  }, [conversations, activeConversationId, activeProfile.defaultContextWindow]);

  if (user === undefined) {
    return (
      <div className="flex h-screen w-screen items-center justify-center text-sm text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <AuthPage onSignedIn={signedInUser => setUser(signedInUser)} />;
  }

  const handleNewConversation = async () => {
    const conversation = await createNewConversation();
    navigate(`/conversations/${conversation.id}`);
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setActiveConversationId(undefined);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    await deleteConversation(conversationId);
    removeConversation(conversationId);
    if (location.pathname.includes(conversationId)) navigate('/');
  };

  const handleSaveContextWindow = async () => {
    if (!activeConversationId) return;
    const trimmed = requestedContextWindow.trim();
    const parsed = trimmed ? Number.parseInt(trimmed, 10) : null;
    if (trimmed && (!parsed || parsed <= 0)) {
      toast.error('Context window must be a positive integer');
      return;
    }
    try {
      await updateConversationSettings(activeConversationId, {
        requested_context_window: parsed,
      });
      await refreshConversations();
      toast.success('Context window updated');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not update context window');
    }
  };

  const handleEjectModel = async () => {
    if (isEjectingModel) return;
    setIsEjectingModel(true);
    try {
      const res = await ejectModel(selectedModel || undefined);
      if (!res.ok) {
        toast.error(res.detail || 'Could not eject model');
        return;
      }
      toast.success(`Ejected model${res.instance_id ? `: ${res.instance_id}` : ''}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not eject model');
    } finally {
      setIsEjectingModel(false);
      const refreshed = await fetchModelsForProfile(activeProfile).catch(() => []);
      if (refreshed.length) setModels(refreshed);
    }
  };

  const handleLoadModel = async () => {
    if (isLoadingModel || !selectedModel) return;
    setIsLoadingModel(true);
    try {
      const contextLength = Number.parseInt(requestedContextWindow || '', 10);
      const res = await loadModel({
        host: activeProfile.host || styleDefaultHost(activeProfile.style),
        api_key: activeProfile.apiKey || '',
        style: activeProfile.style,
        model: selectedModel,
        context_length: Number.isFinite(contextLength) && contextLength > 0 ? contextLength : undefined,
      });
      if (!res.ok) {
        toast.error(res.detail || 'Could not load model');
        return;
      }
      toast.success(`Loaded model: ${selectedModel}`);
      const refreshed = await fetchModelsForProfile(activeProfile).catch(() => []);
      if (refreshed.length) setModels(refreshed);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not load model');
    } finally {
      setIsLoadingModel(false);
    }
  };

  const saveDraftToActiveProfile = () => {
    setProfiles(prev =>
      prev.map(profile =>
        profile.id === activeProfileId
          ? {
              ...profile,
              host: connectionHostDraft,
              apiKey: connectionApiKeyDraft,
              style: connectionStyleDraft,
              chatPath: connectionChatPathDraft,
              modelsPath: connectionModelsPathDraft,
              loadPath: connectionLoadPathDraft,
              unloadPath: connectionUnloadPathDraft,
              defaultModel: defaultModelDraft,
              defaultContextWindow: defaultContextWindowDraft,
            }
          : profile,
      ),
    );
    if (defaultModelDraft) {
      setSelectedModel(defaultModelDraft);
      localStorage.setItem(STORAGE.selectedModel, defaultModelDraft);
    }
    setIsConnectionSettingsOpen(false);
    toast.success('Profile saved');
  };

  const createProfileFromDraft = () => {
    const name = newProfileName.trim();
    if (!name) {
      toast.error('Profile name is required');
      return;
    }
    const id = `${Date.now()}`;
    const profile: ConnectionProfile = {
      id,
      name,
      host: connectionHostDraft,
      apiKey: connectionApiKeyDraft,
      style: connectionStyleDraft,
      chatPath: connectionChatPathDraft,
      modelsPath: connectionModelsPathDraft,
      loadPath: connectionLoadPathDraft,
      unloadPath: connectionUnloadPathDraft,
      defaultModel: defaultModelDraft,
      defaultContextWindow: defaultContextWindowDraft,
    };
    setProfiles(prev => [profile, ...prev]);
    setActiveProfileId(id);
    setNewProfileName('');
    toast.success('Profile created');
  };

  const deleteActiveProfile = () => {
    if (activeProfileId === 'default') {
      toast.error('Default profile cannot be deleted');
      return;
    }
    const next = profiles.filter(profile => profile.id !== activeProfileId);
    setProfiles(next.length ? next : [DEFAULT_PROFILE]);
    setActiveProfileId(next[0]?.id || 'default');
    toast.success('Profile deleted');
  };

  const applySelectedProfile = async () => {
    if (!pendingProfileId || pendingProfileId === activeProfileId) return;
    const target = profiles.find(profile => profile.id === pendingProfileId);
    if (!target) return;
    try {
      const items = await fetchModelsForProfile(target);
      setModels(items);
      setActiveProfileId(pendingProfileId);
      toast.success('Profile selected and models refreshed');
    } catch {
      toast.error('Profile selected, but model refresh failed');
    }
  };

  const verifyConnection = async () => {
    if (isVerifyingConnection) return;
    setIsVerifyingConnection(true);
    try {
      const response = await fetch('/api/connection/verify', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          host: connectionHostDraft,
          api_key: connectionApiKeyDraft,
          style: connectionStyleDraft,
          models_path: connectionModelsPathDraft,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data?.ok) {
        toast.error(data?.detail || 'Connection verify failed');
        return;
      }
      const queried = await queryModels({
        host: connectionHostDraft,
        api_key: connectionApiKeyDraft,
        style: connectionStyleDraft,
        models_path: connectionModelsPathDraft,
      });
      if (queried.length) {
        setModels(queried);
      }
      toast.success(
        `Connection OK (${queried.length || data.models_count || 0} models) via ${data.url || 'target'}`,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Connection verify failed');
    } finally {
      setIsVerifyingConnection(false);
    }
  };

  return (
    <SidebarProvider>
      <div className="flex h-screen w-screen">
        <Sidebar>
          <SidebarHeader>
            <div className="flex items-center justify-between">
              <span className="text-lg font-bold">OpenManus</span>
              <Link
                to="https://github.com/FoundationAgents/OpenManus/tree/openmanus-v2"
                target="_blank"
                rel="noopener noreferrer"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-5 w-5 opacity-80"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <title>GitHub</title>
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
                </svg>
              </Link>
            </div>
            <Button size="sm" className="mt-3 w-full" onClick={handleNewConversation}>
              <Plus className="size-4" />
              New conversation
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="mt-2 w-full"
              onClick={() => {
                setActiveConversationId(undefined);
                navigate('/');
              }}
            >
              <HomeIcon className="size-4" />
              Home
            </Button>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>Model</SidebarGroupLabel>
              <SidebarGroupContent>
                <div className="mx-2 mb-1 text-[11px] text-muted-foreground">
                  Style: {connectionStyleDraft}
                </div>
                <div className="mx-2 mb-2 flex items-center gap-2">
                  <div className="h-8 min-w-0 flex-1 rounded-md border bg-background px-2 text-xs text-muted-foreground flex items-center">
                    Active profile: {activeProfile.name}
                  </div>
                  <Button
                    size="icon"
                    variant="outline"
                    className="h-8 w-8"
                    title="Connection settings"
                    onClick={() => setIsConnectionSettingsOpen(true)}
                  >
                    <SlidersHorizontal className="size-4" />
                  </Button>
                </div>
                <div className="mx-2 flex items-center gap-2">
                  <select
                    className="h-9 min-w-0 flex-1 rounded-md border bg-background px-2 text-sm"
                    value={selectedModel}
                    onChange={event => {
                      setSelectedModel(event.target.value);
                      localStorage.setItem(STORAGE.selectedModel, event.target.value);
                    }}
                  >
                    {groupedFilteredModels.map(([base, variants]) => (
                      <optgroup key={base} label={base}>
                        {variants.map(model => {
                          const variant = String(model.variant_tag || '').trim();
                          const display = variant
                            ? `${base}@${variant}`
                            : model.id;
                          return (
                            <option key={model.id} value={model.id}>
                              {display}
                              {model.state ? ` (${model.state})` : ''}
                            </option>
                          );
                        })}
                      </optgroup>
                    ))}
                  </select>
                  <Button
                    size="icon"
                    variant="outline"
                    title="Load model into runtime memory"
                    onClick={handleLoadModel}
                    disabled={isLoadingModel || !selectedModel}
                  >
                    {isLoadingModel ? (
                      <LoaderCircle className="size-4 animate-spin" />
                    ) : (
                      <Plus className="size-4" />
                    )}
                  </Button>
                  <Button
                    size="icon"
                    variant="outline"
                    title="Eject model from runtime memory"
                    onClick={handleEjectModel}
                    disabled={isEjectingModel || !selectedModel}
                  >
                    {isEjectingModel ? (
                      <LoaderIcon className="size-4 animate-spin" />
                    ) : (
                      <PowerOff className="size-4" />
                    )}
                  </Button>
                </div>
                <div className="mx-2 mt-1 text-[11px] text-muted-foreground">
                  Model status:{' '}
                  <span className={selectedModelLoaded ? 'text-emerald-500' : 'text-amber-500'}>
                    {selectedModelLoaded ? 'Loaded' : 'Unloaded'}
                  </span>
                </div>
                <div className="mx-2 mt-2 space-y-1">
                  <div className="text-xs text-muted-foreground">Requested context window</div>
                  <div className="flex items-center gap-2">
                    <input
                      className="h-8 min-w-0 flex-1 rounded-md border bg-background px-2 text-xs"
                      placeholder="e.g. 128000"
                      value={requestedContextWindow}
                      onChange={event => setRequestedContextWindow(event.target.value)}
                    />
                    <Button size="sm" variant="outline" onClick={handleSaveContextWindow}>
                      Save
                    </Button>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Received:{' '}
                    {(() => {
                      const activeConversation = conversations.find(item => item.id === activeConversationId);
                      const value = activeConversation?.context?.received_window;
                      const source = activeConversation?.context?.received_window_source;
                      const sourceLabel =
                        source === 'lmstudio_load'
                          ? 'confirmed by LM Studio'
                          : source
                            ? 'inferred fallback'
                            : 'unknown source';
                      return value
                        ? `${value.toLocaleString()} (${sourceLabel})`
                        : `-- (${sourceLabel})`;
                    })()}
                  </div>
                </div>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarGroup>
              <SidebarGroupLabel>Conversations</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {conversations.map(item => (
                    <SidebarMenuItem key={item.id}>
                      <div className="group flex items-center gap-1 rounded-md pr-1 hover:bg-muted">
                        <Link
                          to={`/conversations/${item.id}`}
                          onClick={() => setActiveConversationId(item.id)}
                          className={cn(
                            'flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-2 text-sm',
                            (activeConversationId === item.id ||
                              currentTaskId === item.latest_task_id) &&
                              'bg-muted',
                          )}
                        >
                          <MessageSquare className="size-4" />
                          <span className="truncate">{item.title}</span>
                          <span
                            className={cn(
                              'ml-auto text-[10px]',
                              typeof item.context?.usage_ratio === 'number' &&
                                item.context.usage_ratio >= 0.9
                                ? 'text-amber-500'
                                : 'text-muted-foreground',
                            )}
                          >
                            {typeof item.context?.usage_ratio === 'number'
                              ? `${Math.round(item.context.usage_ratio * 100)}%`
                              : '--'}
                          </span>
                        </Link>
                        <Link
                          to={`/conversations/${item.id}/settings`}
                          className="rounded-md p-1.5 opacity-0 hover:bg-background group-hover:opacity-100"
                          title="Conversation settings"
                        >
                          <Settings className="size-4" />
                        </Link>
                        <button
                          className="rounded-md p-1.5 opacity-0 hover:bg-background group-hover:opacity-100"
                          title="Delete conversation"
                          onClick={() => handleDeleteConversation(item.id)}
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </div>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter>
            <div className="space-y-2 p-2">
              <div className="min-w-0 text-sm">
                <div className="flex min-w-0 items-center gap-2">
                  <div className="truncate font-medium">{user.name}</div>
                  {user.role === 'admin' && (
                    <span className="rounded-sm border px-1.5 py-0.5 text-[10px] uppercase tracking-normal text-muted-foreground">
                      Admin
                    </span>
                  )}
                </div>
                <div className="truncate text-xs text-muted-foreground">{user.email}</div>
              </div>
              {user.role === 'admin' && (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => navigate('/admin')}
                >
                  <Shield className="size-4" />
                  Admin
                </Button>
              )}
              <Button variant="outline" size="sm" className="w-full" onClick={handleLogout}>
                <LogOut className="size-4" />
                Sign out
              </Button>
            </div>
          </SidebarFooter>
        </Sidebar>

        <Dialog open={isConnectionSettingsOpen} onOpenChange={setIsConnectionSettingsOpen}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Connection Settings</DialogTitle>
              <DialogDescription>
                Create and load connection profiles with host, style, and endpoint behavior.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-1">
              <div className="space-y-2 rounded-md border p-3">
                <Label className="text-xs">Profile</Label>
                <div className="flex gap-2">
                  <select
                    className="h-9 flex-1 rounded-md border bg-background px-2 text-sm"
                    value={pendingProfileId}
                    onChange={event => {
                      const nextId = event.target.value;
                      setPendingProfileId(nextId);
                      const nextProfile = profiles.find(profile => profile.id === nextId);
                      if (!nextProfile) return;
                      fetchModelsForProfile(nextProfile)
                        .then(items => setModels(items))
                        .catch(() => toast.error('Could not query models for selected profile'));
                    }}
                  >
                    {profiles.map(profile => (
                      <option key={profile.id} value={profile.id}>
                        {profile.name}
                      </option>
                    ))}
                  </select>
                  <Button variant="outline" onClick={applySelectedProfile}>
                    Select profile
                  </Button>
                  <Button
                    variant="outline"
                    onClick={deleteActiveProfile}
                    disabled={activeProfileId === 'default'}
                  >
                    Delete
                  </Button>
                </div>
              </div>

              <div className="space-y-2 rounded-md border p-3">
                <Label className="text-xs">Profile actions</Label>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowProfileOptions(true);
                      setProfileOptionsMode('create');
                    }}
                  >
                    Create profile
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowProfileOptions(true);
                      setProfileOptionsMode('edit');
                    }}
                  >
                    Edit active
                  </Button>
                </div>
              </div>

              {showProfileOptions && (
                <>
                  {profileOptionsMode === 'create' && (
                    <div className="space-y-1 rounded-md border p-3">
                      <Label className="text-xs">Create new profile</Label>
                      <div className="flex gap-2">
                        <Input
                          value={newProfileName}
                          onChange={event => setNewProfileName(event.target.value)}
                          placeholder="e.g. OpenAI Prod"
                          className="h-9 text-sm"
                        />
                        <Button variant="outline" onClick={createProfileFromDraft}>
                          Create
                        </Button>
                      </div>
                    </div>
                  )}

                  <div className="space-y-3 rounded-md border p-3">
                    <div className="text-xs font-medium text-muted-foreground">Connection</div>
                    <div className="space-y-1">
                      <Label className="text-xs">Connection host / IP</Label>
                      <div className="flex gap-2">
                        <Input
                          value={connectionHostDraft}
                          onChange={event => setConnectionHostDraft(event.target.value)}
                          placeholder="http://127.0.0.1:1234"
                          className="h-9 text-sm"
                        />
                        <Button variant="outline" onClick={verifyConnection} disabled={isVerifyingConnection}>
                          {isVerifyingConnection ? <LoaderIcon className="size-4 animate-spin" /> : 'Verify'}
                        </Button>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <div className="w-full space-y-1">
                        <Label className="text-xs">API key</Label>
                        <Input
                          value={connectionApiKeyDraft}
                          onChange={event => setConnectionApiKeyDraft(event.target.value)}
                          placeholder="sk-... (optional)"
                          className="h-9 text-sm"
                        />
                      </div>
                    </div>

                  <div className="space-y-1">
                    <Label className="text-xs">Connection style</Label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={connectionStyleDraft}
                      onChange={event => {
                        const nextStyle = event.target.value as ConnectionStyle;
                        setConnectionStyleDraft(nextStyle);
                        const host = styleDefaultHost(nextStyle);
                        if (host) setConnectionHostDraft(host);
                      }}
                    >
                      <option value="custom">custom</option>
                      <option value="lm-studio">lm-studio</option>
                      <option value="ollama">ollama</option>
                      <option value="openai">openai</option>
                    </select>
                  </div>

                  <div className="rounded-md border bg-muted/30 p-2 text-xs">
                    <div className="mb-1 font-medium">Endpoints for this style</div>
                    <div className="font-mono text-muted-foreground">chat: {styleEndpoints.chat}</div>
                    <div className="font-mono text-muted-foreground">models: {styleEndpoints.models}</div>
                    <div className="font-mono text-muted-foreground">load: {styleEndpoints.load}</div>
                    <div className="font-mono text-muted-foreground">unload: {styleEndpoints.unload}</div>
                  </div>

                  {connectionStyleDraft === 'custom' && (
                    <div className="space-y-2 rounded-md border p-3">
                      <div className="text-xs font-medium">Custom endpoint paths</div>
                      <Input
                        value={connectionChatPathDraft}
                        onChange={event => setConnectionChatPathDraft(event.target.value)}
                        placeholder="/v1/chat/completions"
                        className="h-8 text-xs placeholder:text-muted-foreground/70"
                      />
                      <Input
                        value={connectionModelsPathDraft}
                        onChange={event => setConnectionModelsPathDraft(event.target.value)}
                        placeholder="/v1/models"
                        className="h-8 text-xs placeholder:text-muted-foreground/70"
                      />
                      <Input
                        value={connectionLoadPathDraft}
                        onChange={event => setConnectionLoadPathDraft(event.target.value)}
                        placeholder="/api/v1/models/load"
                        className="h-8 text-xs placeholder:text-muted-foreground/70"
                      />
                      <Input
                        value={connectionUnloadPathDraft}
                        onChange={event => setConnectionUnloadPathDraft(event.target.value)}
                        placeholder="/api/v1/models/unload"
                        className="h-8 text-xs placeholder:text-muted-foreground/70"
                      />
                    </div>
                  )}

                  <div className="space-y-1">
                    <Label className="text-xs">Default model</Label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={defaultModelDraft}
                      onChange={event => setDefaultModelDraft(event.target.value)}
                    >
                      <option value="">(no default)</option>
                      {groupedFilteredModels.map(([base, variants]) => (
                        <optgroup key={`default-${base}`} label={base}>
                          {variants.map(model => {
                            const variant = String(model.variant_tag || '').trim();
                            const display = variant ? `${base}@${variant}` : model.id;
                            return (
                              <option key={`default-${model.id}`} value={model.id}>
                                {display}
                                {model.state ? ` (${model.state})` : ''}
                              </option>
                            );
                          })}
                        </optgroup>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs">Default requested context window</Label>
                    <Input
                      value={defaultContextWindowDraft}
                      onChange={event => setDefaultContextWindowDraft(event.target.value)}
                      placeholder="e.g. 128000"
                      className="h-9 text-sm"
                    />
                  </div>
                  </div>
                </>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setIsConnectionSettingsOpen(false)}>
                Cancel
              </Button>
              <Button onClick={saveDraftToActiveProfile}>Save Profile</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <main className="relative flex-1">
          <Routes>
            <Route path="/" element={<HomePage selectedModel={selectedModel} />} />
            <Route
              path="/conversations/:conversationId"
              element={<TaskDetailPage selectedModel={selectedModel} />}
            />
            <Route path="/conversations/:conversationId/settings" element={<ConversationSettingsPage />} />
            <Route path="/tasks/:taskId" element={<TaskDetailPage selectedModel={selectedModel} />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </main>
        <ConfirmDialog />
      </div>
    </SidebarProvider>
  );
}

export default App;
