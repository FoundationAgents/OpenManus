import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { getAdminSettings, updateAdminSettings, type AdminSettings } from '@/services/admin';
import { Save, ShieldCheck, SlidersHorizontal, Wrench } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

export default function AdminPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [configOverridesText, setConfigOverridesText] = useState('{}');
  const [fallbackChainText, setFallbackChainText] = useState('[]');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    getAdminSettings()
      .then(data => {
        setSettings(data);
        setConfigOverridesText(JSON.stringify(data.config_overrides || {}, null, 2));
        setFallbackChainText(
          JSON.stringify(data.llm_connection?.fallback_chain || [], null, 2),
        );
      })
      .catch(error => toast.error(error.message));
  }, []);

  if (!settings) {
    return <div className="p-6 text-sm text-muted-foreground">Loading admin settings...</div>;
  }

  const disabled = new Set(settings.tools.disabled || []);
  const toggleTool = (name: string) => {
    const next = new Set(disabled);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSettings({ ...settings, tools: { disabled: [...next] } });
  };

  const save = async () => {
    setIsSaving(true);
    try {
      const configOverrides = JSON.parse(configOverridesText || '{}');
      const fallbackChain = JSON.parse(fallbackChainText || '[]');
      if (!Array.isArray(fallbackChain)) {
        throw new Error('Fallback chain must be a JSON array');
      }
      const saved = await updateAdminSettings({
        llm_connection: {
          ...settings.llm_connection,
          fallback_chain: fallbackChain,
        },
        tools: settings.tools,
        config_overrides: configOverrides,
      });
      setSettings(saved);
      setConfigOverridesText(JSON.stringify(saved.config_overrides || {}, null, 2));
      setFallbackChainText(
        JSON.stringify(saved.llm_connection?.fallback_chain || [], null, 2),
      );
      toast.success('Admin settings saved');
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
            <h1 className="text-xl font-semibold">Admin Console</h1>
            <p className="text-sm text-muted-foreground">Runtime connection, overrides, and global capability controls.</p>
          </div>
          <Button onClick={save} disabled={isSaving}>
            <Save className="size-4" />
            Save
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="size-4" />
              Model Connection
            </CardTitle>
            <CardDescription>
              Overrides here become the active runtime defaults for new agent runs.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Model</Label>
                <Input
                  placeholder="qwen3.5-coder"
                  value={settings.llm_connection.model || ''}
                  onChange={event =>
                    setSettings({ ...settings, llm_connection: { ...settings.llm_connection, model: event.target.value } })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">API Type</Label>
                <Input
                  placeholder="openai | lmstudio | ollama | azure"
                  value={settings.llm_connection.api_type || 'openai'}
                  onChange={event =>
                    setSettings({ ...settings, llm_connection: { ...settings.llm_connection, api_type: event.target.value } })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Base URL</Label>
                <Input
                  placeholder="http://127.0.0.1:1234"
                  value={settings.llm_connection.base_url || ''}
                  onChange={event =>
                    setSettings({ ...settings, llm_connection: { ...settings.llm_connection, base_url: event.target.value } })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">API Key</Label>
                <Input
                  placeholder="Optional"
                  type="password"
                  value={settings.llm_connection.api_key || ''}
                  onChange={event =>
                    setSettings({ ...settings, llm_connection: { ...settings.llm_connection, api_key: event.target.value } })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Max Tokens</Label>
                <Input
                  placeholder="4096"
                  type="number"
                  value={settings.llm_connection.max_tokens || ''}
                  onChange={event =>
                    setSettings({
                      ...settings,
                      llm_connection: { ...settings.llm_connection, max_tokens: Number(event.target.value) || undefined },
                    })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">Temperature</Label>
                <Input
                  placeholder="0.7"
                  type="number"
                  step="0.1"
                  value={settings.llm_connection.temperature ?? ''}
                  onChange={event =>
                    setSettings({
                      ...settings,
                      llm_connection: { ...settings.llm_connection, temperature: Number(event.target.value) },
                    })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">
                  Thinking Budget
                  <span className="ml-1 text-amber-500">⚡ reasoning</span>
                </Label>
                <Input
                  placeholder="4096"
                  type="number"
                  value={settings.llm_connection.thinking_budget ?? ''}
                  onChange={event =>
                    setSettings({
                      ...settings,
                      llm_connection: {
                        ...settings.llm_connection,
                        thinking_budget: Number(event.target.value) || undefined,
                      },
                    })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-muted-foreground">
                  Max Agent Steps
                </Label>
                <Input
                  placeholder="30"
                  type="number"
                  value={settings.llm_connection.max_steps ?? ''}
                  onChange={event =>
                    setSettings({
                      ...settings,
                      llm_connection: {
                        ...settings.llm_connection,
                        max_steps: Number(event.target.value) || undefined,
                      },
                    })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Fallback Chain (ordered)</Label>
              <Textarea
                className="min-h-44 font-mono text-xs"
                value={fallbackChainText}
                onChange={event => setFallbackChainText(event.target.value)}
                placeholder={`[
  { "api_type": "lmstudio", "base_url": "http://10.153.2.8:1234", "model": "qwen3.5" },
  { "api_type": "openai", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini" }
]`}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <SlidersHorizontal className="size-4" />
              Runtime Config Overrides
            </CardTitle>
            <CardDescription>
              Global config patch object applied by server-side runtime hooks.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              className="min-h-64 font-mono text-xs"
              value={configOverridesText}
              onChange={event => setConfigOverridesText(event.target.value)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Wrench className="size-4" />
              Global Tools
            </CardTitle>
            <CardDescription>
              Disable or enable capability surfaces for all users. `terminate` remains protected.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-2">
              {settings.available_tools.map(tool => (
                <label key={tool.name} className="flex items-center justify-between rounded-md border p-3 text-sm">
                  <span>
                    <span className="block font-medium">{tool.label}</span>
                    <span className="text-xs text-muted-foreground">{tool.name}</span>
                  </span>
                  <Checkbox
                    checked={!disabled.has(tool.name)}
                    disabled={tool.locked}
                    onCheckedChange={() => toggleTool(tool.name)}
                  />
                </label>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Loaded Config Defaults</CardTitle>
            <CardDescription>Read-only values loaded from configuration sources.</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded-md border bg-muted p-3 text-xs">
              {JSON.stringify(settings.config_defaults || {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
