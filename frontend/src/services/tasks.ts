// 临时的tasks actions文件，用于解决导入错误
// 实际实现需要根据后端API进行调整

export interface CreateTaskParams {
  taskId?: string;
  prompt: string;
}

export interface Task {
  id: string;
  created_at: string;
  request: string;
}

export interface PageTasksParams {
  page: number;
  pageSize: number;
}

export interface PageTasksResult {
  tasks: Task[];
  total: number;
}

export interface GetTaskParams {
  taskId: string;
}

export interface GetTaskEventsParams {
  taskId: string;
}

export interface TerminateTaskParams {
  taskId: string;
}

export interface ShareTaskParams {
  taskId: string;
}

export async function createTask(params: CreateTaskParams): Promise<{ data?: { task_id: string; message: string }; error?: string }> {
  try {
    const formData = new FormData();

    if (params.taskId) {
      formData.append('task_id', params.taskId);
    }
    formData.append('prompt', params.prompt);

    const response = await fetch('/api/tasks', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to create task');
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export function getTaskEvents(params: GetTaskEventsParams): EventSource {
  return new EventSource(`/api/tasks/${params.taskId}/events`);
}

export async function terminateTask(params: TerminateTaskParams): Promise<{ data?: Task; error?: string }> {
  try {
    const response = await fetch(`/api/tasks/${params.taskId}/terminate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to terminate task');
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function pageTasks(params: PageTasksParams): Promise<{ data?: PageTasksResult; error?: string }> {
  try {
    // 这里应该调用实际的API
    const response = await fetch(`/api/tasks?page=${params.page}&pageSize=${params.pageSize}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch tasks');
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' };
  }
}
