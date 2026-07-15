import type { ToolOption } from './admin';

export async function listTools(): Promise<ToolOption[]> {
  const response = await fetch('/api/tools', { credentials: 'same-origin' });
  if (!response.ok) return [];
  const data = await response.json();
  return data.tools || [];
}
