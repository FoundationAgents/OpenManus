export interface Message {
  role: 'user' | 'assistant';
  content: string;
  type?:
    | 'think' // Agent's thoughts
    | 'step' // Step progress
    | 'error' // Error messages
    | 'complete' // Task completion
    | 'tool:selected' // Tool selection
    | 'tool:prepared' // Tool preparation
    | 'tool:arguments' // Tool arguments
    | 'tool:activating' // Tool activation
    | 'tool:completed' // Tool completion
    | 'log'; // Log messages
  step?: number;
  steps?: Message[];
  timestamp?: string;
}

export interface TaskEvent {
  type: 'status' | 'think' | 'tool' | 'act' | 'complete' | 'error';
  data: any;
}

export interface TaskResponse {
  task_id: string;
}
