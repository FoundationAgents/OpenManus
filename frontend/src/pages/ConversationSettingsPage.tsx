import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  getConversation,
  getIntegrationsHealth,
  listSkills,
  updateConversationSettings,
  type Conversation,
  type IntegrationsHealth,
  type SkillSummary,
} from '@/services/conversations';
import { listModels, type ModelOption } from '@/services/models';
import { listTools } from '@/services/tools';
import type { ToolOption } from '@/services/admin';
import { BrainCircuit, RefreshCcw, Save, SlidersHorizontal, Wrench } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';

export default function ConversationSettingsPage() {
  const { conversationId } = useParams();
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [tools, setTools] = useState<ToolOption[]>([]);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [model, setModel] = useState('');
  const [disabledTools, setDisabledTools] = useState<string[]>([]);
  const [disabledSkills, setDisabledSkills] = useState<string[]>([]);
  const [enableVendorSkills, setEnableVendorSkills] = useState(true);
  const [pinnedSkills, setPinnedSkills] = useState<string[]>([]);
  const [identityNotes, setIdentityNotes] = useState('');
  const [autoSkillCurator, setAutoSkillCurator] = useState(true);
  const [maxTokens, setMaxTokens] = useState<number | ''>('');
  const [thinkingBudget, setThinkingBudget] = useState<number | ''>('');
  const [maxSteps, setMaxSteps] = useState<number | ''>('');
  const [enableThinking, setEnableThinking] = useState<'auto' | 'on' | 'off'>('auto');
  const [performanceMode, setPerformanceMode] = useState(false);
  const [health, setHealth] = useState<IntegrationsHealth | null>(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const refreshHealth = async (showErrors = false) => {
    if (!conversationId) return;
    setIsHealthLoading(true);
    try {
      const data = await getIntegrationsHealth(conversationId);
      setHealth(data);
    } catch (error) {
      if (showErrors) {
        toast.error(error instanceof Error ? error.message : 'Could not load integration health');
      }
    } finally {
      setIsHealthLoading(false);
    }
  };

  useEffect(() => {
    if (!conversationId) return;
    Promise.all([getConversation(conversationId), listModels(), listTools(), listSkills(conversationId)])
      .then(([loadedConversation, loadedModels, loadedTools, loadedSkills]) => {
        setConversation(loadedConversation);
        setModels(loadedModels);
        setTools(loadedTools);
        setSkills(loadedSkills.skills || []);
        setModel(loadedConversation.model || loadedModels[0]?.id || '');
        setDisabledTools(loadedConversation.settings?.disabled_tools || []);
        setDisabledSkills(loadedConversation.settings?.disabled_skills || []);
        setEnableVendorSkills(loadedConversation.settings?.enable_vendor_skills ?? true);
        setPinnedSkills(loadedConversation.settings?.pinned_skills || []);
        setIdentityNotes(loadedConversation.settings?.identity_notes || '');
        setAutoSkillCurator(loadedConversation.settings?.auto_skill_curator ?? true);
        setMaxTokens((loadedConversation.settings as any)?.max_tokens ?? '');
        setThinkingBudget((loadedConversation.settings as any)?.thinking_budget ?? '');
        setMaxSteps((loadedConversation.settings as any)?.max_steps ?? '');
        const et = (loadedConversation.settings as any)?.enable_thinking;
        setEnableThinking(et === true ? 'on' : et === false ? 'off' : 'auto');
        setPerformanceMode(Boolean((loadedConversation.settings as any)?.performance_mode));
      })
      .catch(error => toast.error(error instanceof Error ? error.message : 'Could not load settings'));
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;
    refreshHealth();
    const timer = window.setInterval(() => {
      if (!document.hidden) refreshHealth();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [conversationId]);

  if (!conversation || !conversationId) {
    return <div className="p-6 text-sm text-muted-foreground">Loading conversation settings...</div>;
  }

  const disabled = new Set(disabledTools);
  const toggleTool = (name: string) => {
    const next = new Set(disabled);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setDisabledTools([...next]);
  };

  const disabledSkillSet = new Set(disabledSkills);
  const pinnedSkillSet = new Set(pinnedSkills);
  const toggleSkill = (name: string) => {
    const next = new Set(disabledSkillSet);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setDisabledSkills([...next]);
  };

  const togglePinnedSkill = (name: string) => {
    const next = new Set(pinnedSkillSet);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setPinnedSkills([...next]);
  };

  const save = async () => {
    setIsSaving(true);
    try {
      const saved = await updateConversationSettings(conversationId, {
        model,
        disabled_tools: disabledTools,
        disabled_skills: disabledSkills,
        enable_vendor_skills: enableVendorSkills,
        pinned_skills: pinnedSkills,
        identity_notes: identityNotes,
        auto_skill_curator: autoSkillCurator,
        max_tokens: maxTokens !== '' ? maxTokens : undefined,
        thinking_budget: thinkingBudget !== '' ? thinkingBudget : undefined,
        max_steps: maxSteps !== '' ? maxSteps : undefined,
        enable_thinking: enableThinking === 'auto' ? undefined : enableThinking === 'on',
        performance_mode: performanceMode,
      } as any);
      setConversation(saved);
      toast.success('Conversation settings saved');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Could not save settings');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-4">
          <div>
            <h1 className="text-xl font-semibold">{conversation.title}</h1>
            <p className="text-sm text-muted-foreground">Per-conversation model, tools, skills, and memory behavior.</p>
          </div>
          <Button onClick={save} disabled={isSaving}>
            <Save className="size-4" />
            Save
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Integration Health</CardTitle>
              <Button variant="outline" size="sm" onClick={() => refreshHealth(true)} disabled={isHealthLoading}>
                <RefreshCcw className="size-4" />
                Refresh
              </Button>
            </div>
            <CardDescription>Live provider, memory, and vault integration checks.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 md:grid-cols-3">
            <div className="rounded-md border p-3 text-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">AgentMemory</span>
                <span className={health?.agentmemory?.live ? 'text-emerald-500' : health?.agentmemory?.enabled ? 'text-amber-500' : 'text-muted-foreground'}>
                  {health?.agentmemory?.live ? 'Live' : health?.agentmemory?.enabled ? 'Down' : 'Disabled'}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                {health?.agentmemory?.reason || 'Not checked yet'}
              </div>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">Obsidian</span>
                <span className={health?.obsidian?.live ? 'text-emerald-500' : 'text-amber-500'}>
                  {health?.obsidian?.live ? 'Live' : 'Waiting'}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                {health?.obsidian?.reason || 'Not checked yet'}
                {typeof health?.obsidian?.note_count === 'number' ? ` · notes: ${health.obsidian.note_count}` : ''}
              </div>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium">LLM Provider</span>
                <span className={health?.llm_connection?.live ? 'text-emerald-500' : 'text-amber-500'}>
                  {health?.llm_connection?.live ? 'Live' : 'Down'}
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                {health?.llm_connection?.api_type || 'unknown'} · {health?.llm_connection?.reason || 'Not checked yet'}
                {typeof health?.llm_connection?.model_count === 'number'
                  ? ` · models: ${health.llm_connection.model_count}`
                  : ''}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Model</CardTitle>
            <CardDescription>Default model for new runs in this conversation.</CardDescription>
          </CardHeader>
          <CardContent>
            <select
              className="h-10 w-full rounded-md border bg-background px-3 text-sm"
              value={model}
              onChange={event => setModel(event.target.value)}
            >
              {models.map(item => (
                <option key={item.id} value={item.id}>
                  {item.id}
                </option>
              ))}
            </select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="size-4" />
              Tool Permissions
            </CardTitle>
            <CardDescription>Limit tool access for this conversation only.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 md:grid-cols-2">
            {tools.map(tool => {
              const globallyDisabled = tool.enabled === false;
              const enabled = !globallyDisabled && !disabled.has(tool.name);
              return (
                <label key={tool.name} className="flex items-center justify-between rounded-md border p-3 text-sm">
                  <span>
                    <span className="block font-medium">{tool.label}</span>
                    <span className="text-xs text-muted-foreground">
                      {globallyDisabled ? 'Disabled by admin' : tool.name}
                    </span>
                  </span>
                  <Checkbox
                    checked={enabled}
                    disabled={tool.locked || globallyDisabled}
                    onCheckedChange={() => toggleTool(tool.name)}
                  />
                </label>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <BrainCircuit className="size-4" />
                Skill Registry
              </CardTitle>
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <Checkbox checked={enableVendorSkills} onCheckedChange={v => setEnableVendorSkills(Boolean(v))} />
              Enable vendor skills
              </label>
            </div>
            <CardDescription>Enable, disable, and pin skills for execution priority.</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[420px] space-y-2 overflow-auto">
            {skills.map(skill => {
              const enabled = !disabledSkillSet.has(skill.name);
              const pinned = pinnedSkillSet.has(skill.name);
              const fromVendor = skill.path.includes('/vendor/everything-claude-code/');
              return (
                <label key={`${skill.path}:${skill.name}`} className="flex items-center justify-between rounded-md border p-3 text-sm">
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{skill.name}</span>
                    <span className="text-xs text-muted-foreground">{fromVendor ? 'vendor' : 'local'} · {skill.type}</span>
                  </span>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Checkbox
                        checked={pinned}
                        onCheckedChange={() => togglePinnedSkill(skill.name)}
                        disabled={fromVendor && !enableVendorSkills}
                      />
                      Pin
                    </label>
                    <Checkbox
                      checked={enabled}
                      onCheckedChange={() => toggleSkill(skill.name)}
                      disabled={fromVendor && !enableVendorSkills}
                    />
                  </div>
                </label>
              );
            })}
            {!skills.length && <div className="text-sm text-muted-foreground">No skills discovered.</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Skill Curator</CardTitle>
              <label className="flex items-center gap-2 text-xs text-muted-foreground">
                <Checkbox checked={autoSkillCurator} onCheckedChange={v => setAutoSkillCurator(Boolean(v))} />
              Auto-learn tool patterns
              </label>
            </div>
            <CardDescription>Learns repeated successful tool chains from this conversation.</CardDescription>
          </CardHeader>
          <CardContent className="rounded-md border p-3 text-xs text-muted-foreground">
            {(conversation.settings?.skill_suggestions || []).length ? (
              <div className="space-y-2">
                {(conversation.settings?.skill_suggestions || []).slice(0, 8).map(item => (
                  <div key={item.key} className="rounded border p-2">
                    <div className="font-mono text-[11px]">{item.tools.join(' → ')}</div>
                    <div className="text-muted-foreground mt-1">
                      seen {item.count}x
                      {item.last_seen ? ` · ${new Date(item.last_seen * 1000).toLocaleString()}` : ''}
                    </div>
                    {item.last_prompt ? <div className="mt-1 truncate">{item.last_prompt}</div> : null}
                  </div>
                ))}
              </div>
            ) : (
              <div>No learned patterns yet.</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <SlidersHorizontal className="size-4" />
              LLM Limits
            </CardTitle>
            <CardDescription>
              Override max output tokens, thinking budget, and agent steps for this conversation.
              Leave blank to use global defaults.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Max Output Tokens</Label>
                <Input
                  type="number"
                  placeholder="8192 (global default)"
                  value={maxTokens}
                  onChange={e => setMaxTokens(e.target.value === '' ? '' : Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">
                  Thinking Budget
                  <span className="ml-1 text-amber-500">⚡ reasoning</span>
                </Label>
                <Input
                  type="number"
                  placeholder="4096 (global default)"
                  value={thinkingBudget}
                  onChange={e => setThinkingBudget(e.target.value === '' ? '' : Number(e.target.value))}
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Max Agent Steps</Label>
                <Input
                  type="number"
                  placeholder="30 (global default)"
                  value={maxSteps}
                  onChange={e => setMaxSteps(e.target.value === '' ? '' : Number(e.target.value))}
                />
              </div>
            </div>

            {/* Thinking mode control */}
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">
                Thinking / Reasoning Mode
                <span className="ml-1 text-muted-foreground">(auto = detected from LM-Studio or model name)</span>
              </Label>
              <div className="flex gap-2">
                {(['auto', 'on', 'off'] as const).map(option => (
                  <button
                    key={option}
                    onClick={() => setEnableThinking(option)}
                    className={[
                      'rounded-md border px-4 py-1.5 text-sm font-medium transition-colors',
                      enableThinking === option
                        ? option === 'on'
                          ? 'border-amber-500 bg-amber-500/10 text-amber-600'
                          : option === 'off'
                            ? 'border-muted bg-muted text-muted-foreground'
                            : 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-transparent text-muted-foreground hover:bg-muted/40',
                    ].join(' ')}
                  >
                    {option === 'auto' ? '⚙ Auto' : option === 'on' ? '⚡ Always On' : '⊘ Disabled'}
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground">
                {enableThinking === 'auto'
                  ? 'Auto: detected from LM-Studio /api/v0/models or from known model names (Claude 3.7, QwQ, DeepSeek-R1…)'
                  : enableThinking === 'on'
                    ? 'Always on: thinking budget injected into every request for this conversation.'
                    : 'Disabled: thinking tokens suppressed — faster, lower-cost responses.'}
              </p>
            </div>

            {/* Performance mode */}
            <label className="flex cursor-pointer items-center justify-between rounded-md border p-3 text-sm">
              <span>
                <span className="block font-medium">Performance Mode</span>
                <span className="text-xs text-muted-foreground">
                  Disables streaming previews and reduces UI refresh rate. Useful for long background tasks.
                </span>
              </span>
              <Checkbox
                checked={performanceMode}
                onCheckedChange={v => setPerformanceMode(Boolean(v))}
              />
            </label>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Identity Memory</CardTitle>
            <CardDescription>Persistent profile notes injected into every run context.</CardDescription>
          </CardHeader>
          <CardContent>
            <Label className="mb-2 block text-xs text-muted-foreground">Profile Notes</Label>
            <Textarea
              className="min-h-32 text-sm"
              placeholder="Project preferences, coding style, priorities, constraints..."
              value={identityNotes}
              onChange={event => setIdentityNotes(event.target.value)}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
