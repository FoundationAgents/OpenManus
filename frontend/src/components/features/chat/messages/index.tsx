import { Badge } from '@/components/ui/badge';
import { ExpandableContent } from '@/components/features/chat/expandable-content';
import type { Message } from '@/libs/chat-messages';
import { cn } from '@/libs/utils';
import '@/styles/animations.css';

interface ChatMessageProps {
  messages: Message[];
}

const formatTime = (time: Date) => {
  return time.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

// 根据消息类型确定最大显示长度
const getMaxLengthForMessageType = (messageType: string | undefined): number => {
  switch (messageType) {
    case 'tool.toolexecution':
    case 'tool.execution.complete':
      // 工具执行消息通常比较长，设置较短的截断长度
      return 300;
    case 'conversation.agentresponse':
      // AI回复消息可以显示更多内容
      return 800;
    case 'agent.agentstepstart':
    case 'agent.agentstepcomplete':
      // 步骤消息通常较短
      return 200;
    default:
      // 默认长度
      return 500;
  }
};

const StepBadge = ({ message }: { message: Message }) => {
  const eventType = message.type || 'unknown';
  const step = message.step || message.content.step_number;
  const toolName = message.content.tool_name;

  switch (eventType) {
    case 'agent.agentstepstart':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs')}>
          <span className="thinking-animation">🤔</span>
          <span>Step {step} Thinking...</span>
        </Badge>
      );

    case 'agent.agentstepcomplete':
      return (
        <Badge variant="outline" className={cn('text-muted-foreground cursor-pointer font-mono text-xs')}>
          <span>✅</span>
          <span>Step {step} Complete</span>
        </Badge>
      );

    case 'tool.toolexecution':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-blue-50 text-blue-700')}>
          <span>🔧</span>
          <span>Tool: {toolName}</span>
        </Badge>
      );

    case 'tool.execution.complete':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-green-50 text-green-700')}>
          <span>✅</span>
          <span>Tool {toolName} Complete</span>
        </Badge>
      );

    case 'tool.execution.error':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-red-50 text-red-700')}>
          <span>❌</span>
          <span>Tool {toolName} Error</span>
        </Badge>
      );

    case 'agent.task_completed':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-green-50 text-green-700')}>
          <span>🎉</span>
          <span>Task Completed</span>
        </Badge>
      );

    case 'agent.error':
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-red-50 text-red-700')}>
          <span>❌</span>
          <span>Agent Error</span>
        </Badge>
      );

    case 'conversation.agentresponse':
      const responseType = message.content.response_type;
      if (responseType === 'thought') {
        return (
          <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-purple-50 text-purple-700')}>
            <span>💭</span>
            <span>AI Thinking</span>
          </Badge>
        );
      }
      return (
        <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs bg-blue-50 text-blue-700')}>
          <span>💬</span>
          <span>AI Response</span>
        </Badge>
      );

    default:
      return (
        <Badge variant="outline" className={cn('text-muted-foreground cursor-pointer font-mono text-xs')}>
          <span>📝</span>
          <span>{eventType}</span>
        </Badge>
      );
  }
};

const ChatMessage = ({ message, latest }: { message: Message; latest: boolean }) => {
  const agentName = message.content.agent_name || 'Manus';
  const result = message.content.result;
  const startTime = message.createdAt;

  // 只隐藏非最新的步骤开始消息，其他消息都显示
  const hidden = message.type === 'agent.agentstepstart' && !latest;

  if (hidden) return null;

  return (
    <div className="group mb-4 space-y-4">
      <div className="space-y-2">
        <div className="container mx-auto max-w-4xl">
          {/* Message Header */}
          <div className="mb-2 flex items-center justify-between">
            <div className="text-lg font-bold">✨ {agentName}</div>
            {startTime && (
              <div className="text-xs font-medium text-gray-500 italic opacity-0 transition-opacity duration-300 group-hover:opacity-100 hover:opacity-100">
                {formatTime(startTime)}
              </div>
            )}
          </div>

          {/* Step Badge */}
          <div className="text-muted-foreground mt-2 mb-2 font-mono text-xs">
            <StepBadge message={message} />
          </div>

          {/* Result */}
          {result && (
            <ExpandableContent
              content={result}
              maxLength={getMaxLengthForMessageType(message.type)}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export const ChatMessages = ({ messages = [] }: ChatMessageProps) => {
  console.log('messages', messages);
  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <div key={message.index || index} className="first:pt-0">
          <ChatMessage message={message} latest={index === messages.length - 1} />
        </div>
      ))}
    </div>
  );
};
