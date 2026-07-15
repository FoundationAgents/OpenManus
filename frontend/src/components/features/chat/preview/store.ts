import { create } from 'zustand';

export type PreviewData =
  | { type: 'tool'; toolId: string }
  | { type: 'browser'; url: string; title: string; screenshot: string }
  | { type: 'workspace'; path: string }
  | { type: 'live' }
  | { type: 'runtime'; conversationId: string; tab?: 'processes' | 'ports' | 'containers' }
  | { type: 'terminal' }
  | { type: 'changes' }
  | { type: 'skills'; conversationId?: string }
  | { type: 'vault'; conversationId: string };

export const usePreviewData = create<{
  data: PreviewData | null;
  setData: (data: PreviewData | null) => void;
}>(set => ({ data: null, setData: data => set({ data }) }));
