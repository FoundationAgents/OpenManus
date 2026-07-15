export interface ModelOption {
  id: string;
  name: string;
  api_type: string;
  state?: string;
  instance_id?: string;
  base_model?: string;
  variant_tag?: string;
  raw_model_key?: string;
}

export async function listModels(): Promise<ModelOption[]> {
  const response = await fetch('/api/models', { credentials: 'same-origin' });
  if (!response.ok) return [];
  const data = await response.json();
  return data.models || [];
}

export async function queryModels(payload: {
  host: string;
  api_key?: string;
  style: 'lm-studio' | 'ollama' | 'openai' | 'custom';
  models_path?: string;
}): Promise<ModelOption[]> {
  const response = await fetch('/api/models/query', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) return [];
  const data = await response.json().catch(() => ({}));
  return data.models || [];
}

export async function loadModel(payload: {
  host: string;
  api_key?: string;
  style: 'lm-studio' | 'ollama' | 'openai' | 'custom';
  model: string;
  context_length?: number;
}): Promise<{ ok: boolean; detail?: string }> {
  const response = await fetch('/api/models/load', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data?.ok) {
    return { ok: false, detail: data?.detail || 'Could not load model' };
  }
  return { ok: true };
}

export async function ejectModel(model?: string): Promise<{ ok: boolean; instance_id?: string; detail?: string }> {
  const response = await fetch('/api/models/eject', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(model ? { model } : {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return { ok: false, detail: data?.detail || 'Could not eject model' };
  }
  return { ok: true, instance_id: data?.instance_id };
}
