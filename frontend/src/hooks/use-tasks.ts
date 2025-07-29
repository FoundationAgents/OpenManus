import { create } from 'zustand';

export interface Task {
  id: string;
  created_at: string;
  request: string;
  status: 'initializing' | 'running' | 'completed' | 'error' | 'paused';
  progress: number;
}

interface TaskStore {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  refreshTasks: () => Promise<void>;
  deleteTask: (taskId: string) => Promise<boolean>;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
}

export const useRecentTasks = create<TaskStore>((set, get) => ({
  tasks: [],
  isLoading: false,
  error: null,

  refreshTasks: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch('/api/manus/sessions');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const tasks: Task[] = (data.sessions || []).map((session: any) => ({
        id: session.session_id,
        created_at: new Date().toISOString(), // API doesn't return created_at yet
        request: session.prompt || 'Untitled Task',
        status: session.status || 'initializing',
        progress: session.progress || 0,
      }));

      set({ tasks, isLoading: false });
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch tasks',
        isLoading: false
      });
    }
  },

  deleteTask: async (taskId: string) => {
    try {
      const response = await fetch(`/api/manus/sessions/${taskId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Remove from local state
      const { tasks } = get();
      set({ tasks: tasks.filter(task => task.id !== taskId) });
      return true;
    } catch (error) {
      console.error('Failed to delete task:', error);
      set({ error: 'Failed to delete task' });
      return false;
    }
  },

  addTask: (task: Task) => {
    const { tasks } = get();
    set({ tasks: [task, ...tasks] });
  },

  updateTask: (taskId: string, updates: Partial<Task>) => {
    const { tasks } = get();
    set({
      tasks: tasks.map(task =>
        task.id === taskId ? { ...task, ...updates } : task
      )
    });
  },
}));
