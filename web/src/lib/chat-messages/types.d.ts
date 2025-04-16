type AgentLifecycleStepActToolType =
  | 'agent:lifecycle:step:act:tool:start'
  | 'agent:lifecycle:step:act:tool:execute:start'
  | 'agent:lifecycle:step:act:tool:execute:complete'
  | 'agent:lifecycle:step:act:tool:complete'
  | 'agent:lifecycle:step:act:tool:error';

type AgentLifecycleStepThinkBrowserType =
  | 'agent:lifecycle:step:think:browser:browse:start'
  | 'agent:lifecycle:step:think:browser:browse:complete'
  | 'agent:lifecycle:step:think:browser:browse:error';

type AgentLifecycleStepThinkType =
  | AgentLifecycleStepThinkBrowserType
  | 'agent:lifecycle:step:think:start'
  | 'agent:lifecycle:step:think:tool:selected'
  | 'agent:lifecycle:step:think:token:count'
  | 'agent:lifecycle:step:think:complete';

type AgentLifecycleStepActType =
  | AgentLifecycleStepActToolType
  | 'agent:lifecycle:step:act:start'
  | 'agent:lifecycle:step:act:token:count'
  | 'agent:lifecycle:step:act:complete';

type AgentLifecycleStepType =
  | AgentLifecycleStepThinkType
  | AgentLifecycleStepActType
  | 'agent:lifecycle:step:start'
  | 'agent:lifecycle:step:complete'
  | 'agent:lifecycle:step:error';

type AgentLifecycleType =
  | AgentLifecycleStepType
  | 'agent:lifecycle:start'
  | 'agent:lifecycle:plan'
  | 'agent:lifecycle:memory:added'
  | 'agent:lifecycle:state:change'
  | 'agent:lifecycle:complete'
  | 'agent:lifecycle:terminated';

type AggregatedMessageType =
  | 'agent:lifecycle'
  | 'agent:lifecycle:step'
  | 'agent:lifecycle:step:think'
  | 'agent:lifecycle:step:act'
  | 'agent:lifecycle:step:act:tool'
  | 'agent:lifecycle:step:act:browser';

/**
 * agent:step:start
 *   agent:think:start
 *     agent:tool:selected
 *     agent:think:token:count
 *   agent:think:complete
 *   agent:act:start
 *     agent:tool:start
 *         agent:tool:execute:start
 *         agent:tool:execute:complete
 *     agent:tool:complete
 *     agent:act:token:count
 *   agent:act:complete
 * agent:step:complete
 */
export type Message<T = any> = {
  index?: number;
  role: 'user' | 'assistant';
  createdAt?: Date;
  type?: AgentLifecycleType;
  step?: number;
  content: T;
};

export type AggregatedMessage = Omit<Message, 'type'> &
  ({ type?: AggregatedMessageType; messages: (Message | AggregatedMessage)[] } | { type?: AgentLifecycleType });
