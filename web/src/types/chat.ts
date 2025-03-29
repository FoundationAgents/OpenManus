export type Message<T = any> = {
  role: 'user' | 'assistant';
  index?: number;
  timestamp?: string;
  step?: number;
  type?:
    | 'agent:step:start'
    | 'agent:step:complete'
    | 'agent:step:error'
    | 'agent:memory:added'
    | 'agent:state:change'
    | 'agent:tool:selected'
    | 'agent:tool:start'
    | 'agent:tool:complete'
    | 'agent:browser:browse:start'
    | 'agent:browser:browse:complete'
    | 'agent:tool:selected'
    | 'agent:tool:start'
    | 'agent:tool:complete'
    | 'agent:tool:execute:start'
    | 'agent:tool:execute:complete'
    | 'agent:browser:screenshot:capture'
    | 'agent:tool:selected'
    | 'agent:tool:start'
    | 'agent:tool:complete'
    | 'agent:state:change'
    | 'agent:lifecycle:complete';
  content: T;
};

export type AggregatedMessage = Message | { role: 'assistant'; type: 'tool'; messages: Message[]; step?: number; timestamp?: string; index?: number };

export interface TaskEvent {
  type: 'status' | 'think' | 'tool' | 'act' | 'complete' | 'error';
  data: any;
}

export interface TaskResponse {
  task_id: string;
}
