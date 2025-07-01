import type { AggregatedMessage, Message } from './types';

class ChatMessageAggregator {
  private _messages: Message[] = [];
  private _aggregatedMessages: AggregatedMessage[] = [];

  get aggregatedMessages() {
    return this._aggregatedMessages;
  }

  get messages() {
    return this._messages;
  }

  constructor(messages: Message[]) {
    this._messages = messages;
    this.aggregate();
  }

  private aggregate() {
    let currentLifecycle: AggregatedMessage | null = null;
    let currentStep: AggregatedMessage | null = null;
    let currentThink: AggregatedMessage | null = null;
    let currentAct: AggregatedMessage | null = null;
    let currentTool: AggregatedMessage | null = null;
    let currentBrowser: AggregatedMessage | null = null;
    let currentPlan: AggregatedMessage | null = null;
    let currentPrepare: AggregatedMessage | null = null;

    for (const message of this._messages) {
      // Handle non-lifecycle messages
      if (!message.type?.startsWith('agent:lifecycle')) {
        this._aggregatedMessages.push(message);
        continue;
      }

      // Start new lifecycle if needed
      if (message.type === 'agent:lifecycle:start') {
        if (currentLifecycle) {
          this._aggregatedMessages.push(currentLifecycle);
        }
        currentLifecycle = {
          ...message,
          type: 'agent:lifecycle',
          messages: [message],
        };
        continue;
      }

      // Handle plan messages
      if (message.type?.startsWith('agent:lifecycle:plan')) {
        if (message.type === 'agent:lifecycle:plan:start') {
          currentPlan = {
            ...message,
            type: 'agent:lifecycle:plan',
            messages: [message],
          } as AggregatedMessage;
          if (currentLifecycle && 'messages' in currentLifecycle) {
            currentLifecycle.messages.push(currentPlan);
          }
        } else if (currentPlan && 'messages' in currentPlan) {
          currentPlan.messages.push(message);
        }
        continue;
      }

      // Handle prepare messages
      if (message.type?.startsWith('agent:lifecycle:prepare')) {
        if (message.type === 'agent:lifecycle:prepare:start') {
          currentPrepare = {
            ...message,
            type: 'agent:lifecycle:prepare',
            messages: [message],
          } as AggregatedMessage;
          if (currentLifecycle && 'messages' in currentLifecycle) {
            currentLifecycle.messages.push(currentPrepare);
          }
        } else if (currentPrepare && 'messages' in currentPrepare) {
          currentPrepare.messages.push(message);
        }
        continue;
      }

      // Handle top-level lifecycle messages
      if (
        message.type === 'agent:lifecycle:complete' ||
        message.type === 'agent:lifecycle:terminated' ||
        message.type === 'agent:lifecycle:memory:added' ||
        message.type === 'agent:lifecycle:state:change'
      ) {
        if (currentLifecycle && 'messages' in currentLifecycle) {
          currentLifecycle.messages.push(message);
        }
        continue;
      }

      // Handle step messages
      if (message.type === 'agent:lifecycle:step:start') {
        currentStep = {
          ...message,
          type: 'agent:lifecycle:step',
          messages: [message],
        };
        if (currentLifecycle && 'messages' in currentLifecycle) {
          currentLifecycle.messages.push(currentStep);
        }
        continue;
      }

      // Handle think messages
      if (message.type?.startsWith('agent:lifecycle:step:think')) {
        if (message.type === 'agent:lifecycle:step:think:start') {
          currentThink = {
            ...message,
            type: 'agent:lifecycle:step:think',
            messages: [message],
          };
          if (currentStep && 'messages' in currentStep) {
            currentStep.messages.push(currentThink);
          }
        } else if (currentThink && 'messages' in currentThink) {
          currentThink.messages.push(message);
        }
        continue;
      }

      // Handle act messages
      if (message.type?.startsWith('agent:lifecycle:step:act')) {
        if (message.type === 'agent:lifecycle:step:act:start') {
          currentAct = {
            ...message,
            type: 'agent:lifecycle:step:act',
            messages: [message],
          };
          if (currentStep && 'messages' in currentStep) {
            currentStep.messages.push(currentAct);
          }
          continue;
        }

        // Handle tool messages
        if (message.type?.includes(':tool:')) {
          if (message.type === 'agent:lifecycle:step:act:tool:start') {
            currentTool = {
              ...message,
              type: 'agent:lifecycle:step:act:tool',
              messages: [message],
            };
            if (currentAct && 'messages' in currentAct) {
              currentAct.messages.push(currentTool);
            }
          } else if (currentTool && 'messages' in currentTool) {
            currentTool.messages.push(message);
          }
          continue;
        }

        // Handle browser messages
        if (message.type?.includes(':browser:')) {
          if (message.type === 'agent:lifecycle:step:think:browser:browse:complete') {
            currentBrowser = {
              ...message,
              type: 'agent:lifecycle:step:act:browser',
              messages: [message],
            };
            if (currentAct && 'messages' in currentAct) {
              currentAct.messages.push(currentBrowser);
            }
          } else if (currentBrowser && 'messages' in currentBrowser) {
            currentBrowser.messages.push(message);
          }
          continue;
        }

        // Handle other act messages
        if (currentAct && 'messages' in currentAct) {
          currentAct.messages.push(message);
        }
        continue;
      }

      // Handle step completion
      if (message.type === 'agent:lifecycle:step:complete' || message.type === 'agent:lifecycle:step:error') {
        if (currentStep && 'messages' in currentStep) {
          currentStep.messages.push(message);
          // Reset step-related references
          currentThink = null;
          currentAct = null;
          currentTool = null;
          currentBrowser = null;
          currentStep = null;
        }
      }
    }

    // Add the last lifecycle if exists
    if (currentLifecycle) {
      this._aggregatedMessages.push(currentLifecycle);
    }
  }
}

export const aggregateMessages = (messages: Message[]) => {
  return new ChatMessageAggregator(messages).aggregatedMessages;
};
