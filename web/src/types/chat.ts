export type Message = {
  role: 'user' | 'assistant';
  content: string;
  type?:
    | 'think' // Agent's thoughts
    | 'step' // Step progress
    | 'error' // Error messages
    | 'complete' // Task completion
    | 'result' // Result messages
    | 'tool:selected' // Tool selection
    | 'tool:prepared' // Tool preparation
    | 'tool:arguments' // Tool arguments
    | 'tool:activating' // Tool activation
    | 'tool:completed' // Tool completion
    | 'token-usage' // Token usage
    | 'log'; // Log messages
  step?: number;
  timestamp?: string;
  index?: number;
};

export type AggregatedMessage = Message | { role: 'assistant'; type: 'tool'; messages: Message[]; step?: number; timestamp?: string; index?: number };

export interface TaskEvent {
  type: 'status' | 'think' | 'tool' | 'act' | 'complete' | 'error';
  data: any;
}

export interface TaskResponse {
  task_id: string;
}
