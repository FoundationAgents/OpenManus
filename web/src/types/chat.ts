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
    | 'agent:think:start'
    | 'agent:think:token:count'
    | 'agent:think:complete'
    | 'agent:act:start'
    | 'agent:act:token:count'
    | 'agent:act:complete'
    | 'agent:tool:selected'
    | 'agent:tool:start'
    | 'agent:tool:complete'
    | 'agent:browser:browse:start'
    | 'agent:browser:browse:complete'
    | 'agent:browser:browse:error'
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

type AggregatedMessageType = 'tool' | 'step';

export type AggregatedMessage<T extends AggregatedMessageType | Message['type'] = AggregatedMessageType | Message['type']> =
  T extends AggregatedMessageType ? { role: 'assistant'; type: T; messages: Message[]; step?: number; timestamp?: string; index?: number } : Message;

export interface TaskEvent {
  type: 'status' | 'think' | 'tool' | 'act' | 'complete' | 'error';
  data: any;
}

export interface TaskResponse {
  task_id: string;
}
