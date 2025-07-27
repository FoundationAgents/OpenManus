import { create } from 'zustand';

export interface Task {
  id: string;
  created_at: string;
  request: string;
}

export const useRecentTasks = create<{ tasks: Task[]; refreshTasks: () => Promise<void> }>(set => ({
  tasks: [],
  refreshTasks: async () => {
    // TODO: Implement actual task list retrieval in the future
    // For now, return empty array
    set({ tasks: [] });
  },
}));
