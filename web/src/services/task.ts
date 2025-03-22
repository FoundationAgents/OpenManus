import { Message, TaskResponse } from '../types/chat';

const API_BASE_URL = 'http://localhost:5172';

export const createTask = async (prompt: string, signal?: AbortSignal): Promise<TaskResponse> => {
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt }),
    signal,
  });

  if (!response.ok) {
    throw new Error('Failed to create task');
  }

  return response.json();
};

export const getTaskEvents = async (taskId: string, signal?: AbortSignal): Promise<Response> => {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/events`, {
    signal,
  });

  if (!response.ok) {
    throw new Error('Failed to get task events');
  }

  return response;
};

export const handleTaskEventsStreamResponse = async (response: Response, onMessage: (messages: Message[]) => void) => {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Failed to get response stream');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            break;
          }
          try {
            const parsed = JSON.parse(data);
            // only handle status event, any status event contains all steps info
            if (parsed.type === 'status') {
              onMessage(
                parsed.steps.map((step: any) => ({
                  role: 'assistant',
                  content: step.result,
                  type: step.type,
                  step: step.step,
                }))
              );
            }
          } catch (error) {
            console.error('Failed to parse response data:', error);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};
