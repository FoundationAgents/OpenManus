import { pageTasks, type Task } from '@/services/tasks';
import { create } from 'zustand';

export const useRecentTasks = create<{ tasks: Task[]; refreshTasks: () => Promise<void> }>(set => ({
  tasks: [],
  refreshTasks: async () => {
    const res = await pageTasks({ page: 1, pageSize: 30 });
    set({ tasks: res.data?.tasks || [] });
  },
}));
