import { Badge } from '@/components/ui/badge';
import { ExpandableContent } from '@/components/features/chat/expandable-content';
import type { Message } from '@/libs/chat-messages';
import { cn } from '@/libs/utils';
import '@/styles/animations.css';
import { Markdown } from '@/components/block/markdown';
import { usePreviewData } from '../preview/store';

interface ChatMessageProps {
  messages: Message[];
  className?: string;
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

const StepBadge = ({ thinking, step }: { thinking: boolean; step: number }) => {
  if (thinking) {
    return (
      <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs')}>
        <span className="thinking-animation">🤔</span>
        <span>Step {step} Thinking...</span>
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs')}>
      <span>🚀</span>
      <span>Step {step} Complete</span>
    </Badge>
  );
};

const ToolBadge = ({ toolName, executing, onClick }: { toolName: string; executing: boolean; onClick: () => void }) => {
  return (
    <Badge variant="outline" className={cn('cursor-pointer font-mono text-xs')} onClick={onClick}>
      <span>{executing ? '🔧' : '🎯'}</span>
      <span>
        Tool: {toolName} {executing ? 'Executing...' : 'Complete'}
      </span>
    </Badge>
  );
};

const UserInputMessage = ({ message }: { message: Message }) => {
  // 提取用户消息内容，支持多种格式
  let content = '';
  if (typeof message.content === 'string') {
    content = message.content;
  } else if (message.content?.message) {
    content = message.content.message;
  } else if (message.content?.input) {
    content = message.content.input;
  } else if (message.content?.content) {
    content = message.content.content;
  } else {
    content = JSON.stringify(message.content);
  }

  const createdAt = message.createdAt;

  return (
    <div className="group mb-4 space-y-4">
      <div className="space-y-2">
        <div className="container mx-auto flex w-full flex-row-reverse">
          <Markdown className="chat w-fit max-w-[calc(100%-100px)]">{content}</Markdown>
        </div>
      </div>
    </div>
  );
};

const ChatMessage = ({ messages }: { messages: Message[] }) => {
  const { setData } = usePreviewData();

  const stepStart = messages.find(message => message.type === 'agent.agentstepstart');
  const stepComplete = messages.find(message => message.type === 'agent.agentstepcomplete');
  const agentResponse = messages.find(message => message.type === 'conversation.agentresponse');
  const toolExecution = messages.find(message => message.type === 'tool.toolexecution');
  const toolResult = messages.find(message => message.type === 'tool.toolresult');

  const step = stepStart?.step || stepComplete?.step || 0;
  const agentName = stepStart?.content.agent_name || 'Manus';
  const startTime = stepStart?.createdAt;

  const toolName = toolExecution?.content.tool_name || toolResult?.content.tool_name || '';

  // 只隐藏非最新的步骤开始消息，其他消息都显示
  const thinking = !stepComplete;
  const toolExecuting = !!(toolExecution && !toolResult);

  const thoughtContent = agentResponse?.content.result;

  return (
    <div className="group mb-4 space-y-4">
      <div className="space-y-2">
        <div className="container mx-auto max-w-4xl">
          {/* Message Header, Only step start and step complete show header */}
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
            <StepBadge thinking={thinking} step={step} />
          </div>

          {/* Result */}
          {thoughtContent && <ExpandableContent content={thoughtContent} maxLength={500} className="w-fit max-w-[calc(100%-100px)]" />}
          {(toolExecution || toolResult) && (
            <div className="text-muted-foreground mt-2 mb-2 font-mono text-xs">
              <ToolBadge
                toolName={toolName}
                executing={toolExecuting}
                onClick={() => setData({ type: 'tool', toolId: toolExecution?.content.execution_id })}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const ChatMessages = ({ messages = [], className }: ChatMessageProps) => {
  console.log('messages', messages);
  return (
    <div className={cn('space-y-4', className)}>
      {aggregateMessages(messages).map((msgs, index) => {
        // 检查是否为用户输入消息组
        if (msgs.length === 1 && msgs[0].type === 'conversation.userinput') {
          return (
            <div key={index} className="first:pt-0">
              <UserInputMessage message={msgs[0]} />
            </div>
          );
        }

        // 其他情况使用 ChatMessage 组件
        return (
          <div key={index} className="first:pt-0">
            <ChatMessage messages={msgs} />
          </div>
        );
      })}
    </div>
  );
};

const aggregateMessages = (messages: Message[]) => {
  const aggregatedMessages: Message[][] = [];
  let currentAgentGroup: Message[] = [];
  let hasAgentGroup = false;

  for (const message of messages) {
    if (message.type === 'conversation.userinput') {
      // 如果当前有 agent 组，先保存它
      if (hasAgentGroup && currentAgentGroup.length > 0) {
        aggregatedMessages.push([...currentAgentGroup]);
        currentAgentGroup = [];
        hasAgentGroup = false;
      }
      // userinput 消息独立成组
      aggregatedMessages.push([message]);
    } else if (message.type === 'agent.agentstepstart') {
      // 如果当前有 agent 组，先保存它
      if (hasAgentGroup && currentAgentGroup.length > 0) {
        aggregatedMessages.push([...currentAgentGroup]);
      }
      // 开始新的 agent 组
      currentAgentGroup = [message];
      hasAgentGroup = true;
    } else {
      // 其他消息添加到当前 agent 组
      if (hasAgentGroup) {
        currentAgentGroup.push(message);
      } else {
        // 如果没有 agent 组，创建独立组
        aggregatedMessages.push([message]);
      }
    }
  }

  // 保存最后一个 agent 组
  if (hasAgentGroup && currentAgentGroup.length > 0) {
    aggregatedMessages.push(currentAgentGroup);
  }

  return aggregatedMessages;
};
