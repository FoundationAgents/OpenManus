import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { ManusMessageSocket, type ManusMessage, type Message, type MessageType } from '@/libs/chat-messages';
import { EventSender } from '@/libs/event-sender';
import { FrontendEventHandler, type BackendEvent } from '@/libs/event-handler';
import { type WebSocketState } from '@/libs/websocket/types';
import { useRecentTasks } from '@/hooks/use-tasks';
import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

const useConversation = (taskId: string | undefined) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [taskStatus, setTaskStatus] = useState<'idle' | 'running' | 'paused' | 'completed' | 'error'>('idle');
  const [agentStatus, setAgentStatus] = useState<'idle' | 'thinking' | 'acting' | 'waiting'>('idle');
  const [currentStep, setCurrentStep] = useState(0);
  const [currentTool, setCurrentTool] = useState<string>('');
  const [waitingForInput, setWaitingForInput] = useState(false);
  const [inputPrompt, setInputPrompt] = useState<string>('');

  const eventSenderRef = useRef<EventSender | null>(null);
  const eventHandlerRef = useRef<FrontendEventHandler | null>(null);
  const isInitializedRef = useRef<boolean>(false); // 添加初始化标志
  const unsubscribersRef = useRef<(() => void)[]>([]); // 存储取消订阅函数，防止重复注册

  // 使用useMemo确保streamRef只创建一次
  const streamRef = useRef<ManusMessageSocket<ManusMessage> | null>(null);

  // 初始化streamRef（只在第一次时创建）
  if (!streamRef.current) {
    streamRef.current = new ManusMessageSocket<ManusMessage>({
      url: '',
      onMessage: (message: Message) => {
        // MessageStream处理转换后的消息，用于UI显示
        console.log('📝 MessageStream received message:', message);
        setMessages(prev => [...prev, message]);
      },
    });
  }

  // Auto-connect when component mounts
  useEffect(() => {
    console.log('🔄 useEffect执行 - taskId:', taskId, 'unsubscribers:', unsubscribersRef.current.length);
    if (!taskId) return;

    // 清空之前任务的消息，准备加载新任务的历史消息
    setMessages([]);
    if (streamRef.current) {
      streamRef.current.clearMessages();
    }
    console.log('🧹 已清空之前任务的消息，准备加载新任务');

    const initializeEventSystem = () => {
      // 防止重复初始化
      if (isInitializedRef.current) {
        console.debug('Event system already initialized, skipping');
        return;
      }

      if (!streamRef.current) {
        console.warn('StreamRef not available, cannot initialize event system');
        return;
      }

      const wsAdapter = streamRef.current.getWebSocketAdapter();

      try {
        // 创建事件发送器和处理器
        eventSenderRef.current = new EventSender(wsAdapter);
        eventHandlerRef.current = new FrontendEventHandler();

        // 设置事件处理器
        setupEventHandlers(eventHandlerRef.current, taskId);

        // 标记为已初始化
        isInitializedRef.current = true;

        console.log('Event system initialized for task:', taskId);
      } catch (error) {
        console.error('Failed to initialize event system:', error);
      }
    };

    // 连接WebSocket（只在第一次或taskId变化时）
    if (streamRef.current && unsubscribersRef.current.length === 0) {
      const wsAdapter = streamRef.current.getWebSocketAdapter();

      // 监听连接状态变化
      const unsubscribeState = wsAdapter.onState((state: WebSocketState) => {
        if (state === 'connected') {
          initializeEventSystem();
        }
      });

      // 监听WebSocket消息，处理事件类型的消息
      const unsubscribeMessage = wsAdapter.onMessage((message: any) => {
        // 处理事件类型的消息（包括实时事件和历史消息）
        if ((message.type === 'event' || message.type === 'agent_event') && eventHandlerRef.current) {
          // 检查事件是否属于当前task
          const eventTaskId = message.conversation_id || message.session_id || message.data?.conversation_id || message.data?.session_id;
          if (eventTaskId && eventTaskId !== taskId) {
            console.debug('Ignoring event for different task:', eventTaskId, 'current:', taskId);
            return;
          }

          // 转换历史消息格式为事件格式
          let eventMessage = message;
          if (message.type === 'agent_event') {
            eventMessage = {
              type: 'event',
              event_type: message.event_type,
              event_id: `history_${Date.now()}_${Math.random()}`,
              data: message.data || {},
              timestamp: message.timestamp,
              source: 'backend',
            };
          }

          eventHandlerRef.current.handleEvent(eventMessage as BackendEvent);
        }
        // 检查是否是连接确认消息
        else if (message.type === 'connection_established') {
          initializeEventSystem();
        }
      });

      // 存储取消订阅函数，防止重复注册
      unsubscribersRef.current = [unsubscribeState, unsubscribeMessage];
      console.log('✅ WebSocket监听器已注册');

      // 检查当前连接状态，避免重复连接
      const currentState = wsAdapter.currentState;

      if (currentState === 'idle' || currentState === 'error') {
        // 开始连接
        streamRef.current.connect(`ws://localhost:8000/api/manus/sessions/ws/${taskId}`);
      } else if (currentState === 'connected') {
        // 如果已经连接，直接初始化事件系统
        initializeEventSystem();
      }

      // 延迟检查连接状态并初始化
      setTimeout(initializeEventSystem, 500);

      // 返回清理函数
      return () => {
        console.log('🧹 清理WebSocket监听器...');
        // 清理WebSocket监听器
        unsubscribersRef.current.forEach(unsubscribe => unsubscribe());
        unsubscribersRef.current = [];

        if (streamRef.current) {
          streamRef.current.disconnect();
        }
        eventSenderRef.current = null;
        eventHandlerRef.current = null;
        isInitializedRef.current = false; // 重置初始化标志
      };
    }

    // 如果没有streamRef或已经注册过监听器，返回空的清理函数
    return () => {
      console.log('⏭️ 跳过WebSocket初始化（已存在或无streamRef）');
    };
  }, [taskId]); // 只在taskId变化时重新执行

  // 创建消息的辅助函数
  const createMessageFromEvent = (event: BackendEvent): Message => {
    return {
      index: Date.now() + Math.random(), // 使用时间戳+随机数确保唯一性
      role: 'assistant' as const,
      content: {
        agent_name: event.data.agent_name || 'Manus',
        step_number: event.data.step_number,
        result: event.data.result || event.data.message,
        tool_name: event.data.tool_name,
        ...event.data,
      },
      createdAt: new Date(),
      type: event.event_type as MessageType,
      step: event.data.step_number,
    };
  };

  // 设置事件处理器
  const setupEventHandlers = (eventHandler: FrontendEventHandler, _conversationId: string) => {
    // 监听智能体事件
    eventHandler.on('agent.*', (event: BackendEvent) => {
      console.log('Agent event:', event.event_type);

      // 更新状态
      switch (event.event_type) {
        case 'agent.agentstepstart':
          setTaskStatus('running');
          setAgentStatus('thinking');
          setCurrentStep(event.data.step_number || 1);
          console.log(`🚀 开始执行步骤 ${event.data.step_number}`);

          // 创建步骤开始消息
          const startMessage = createMessageFromEvent(event);
          setMessages(prev => [...prev, startMessage]);
          break;

        case 'agent.agentstepcomplete':
          // 步骤完成后，检查是否还有更多步骤
          setAgentStatus('idle');
          console.log(`✅ 步骤 ${currentStep} 完成`);

          // 创建步骤完成消息
          const completeMessage = createMessageFromEvent(event);
          setMessages(prev => [...prev, completeMessage]);

          // 如果是最后一步或者智能体决定终止，则标记为完成
          if (event.data.result && event.data.result.includes('Terminated')) {
            setTaskStatus('completed');
            console.log('🎉 任务完成');
          }
          break;

        case 'agent.task_completed':
          setTaskStatus('completed');
          setAgentStatus('idle');
          console.log('🎉 任务完成');

          // 创建任务完成消息
          const taskCompleteMessage = createMessageFromEvent(event);
          setMessages(prev => [...prev, taskCompleteMessage]);
          break;

        case 'agent.error':
          setTaskStatus('error');
          setAgentStatus('idle');
          console.log('❌ 智能体执行出错');

          // 创建错误消息
          const errorMessage = createMessageFromEvent(event);
          setMessages(prev => [...prev, errorMessage]);
          break;
      }
    });

    // 监听工具执行事件
    eventHandler.on('tool.*', (event: BackendEvent) => {
      console.log('Tool event:', event.event_type);

      switch (event.event_type) {
        case 'tool.toolexecution':
          setAgentStatus('acting');
          setCurrentTool(event.data.tool_name || '');
          console.log(`🔧 开始执行工具: ${event.data.tool_name}`);

          // 创建工具开始执行消息
          const toolStartMessage = createMessageFromEvent(event);
          toolStartMessage.content.result = `🔧 开始执行工具: ${event.data.tool_name}`;
          setMessages(prev => [...prev, toolStartMessage]);
          break;

        case 'tool.execution.complete':
          const toolName = currentTool || event.data.tool_name;
          console.log(`✅ 工具执行完成: ${toolName}`);

          // 创建工具完成消息
          const toolCompleteMessage = createMessageFromEvent(event);
          toolCompleteMessage.content.result = event.data.result || `✅ 工具 ${toolName} 执行完成`;
          setMessages(prev => [...prev, toolCompleteMessage]);

          // 如果是terminate工具，标记任务完成
          if (toolName === 'terminate') {
            setTaskStatus('completed');
            setAgentStatus('idle');
            console.log('🎉 任务通过terminate工具完成');
          } else {
            setAgentStatus('thinking');
          }
          setCurrentTool('');
          break;

        case 'tool.execution.error':
          setAgentStatus('idle');
          setCurrentTool('');
          console.log(`❌ 工具执行失败: ${currentTool}`);

          // 创建工具错误消息
          const toolErrorMessage = createMessageFromEvent(event);
          toolErrorMessage.content.result = `❌ 工具执行失败: ${event.data.error || '未知错误'}`;
          setMessages(prev => [...prev, toolErrorMessage]);
          break;
      }
    });

    // 监听对话事件
    eventHandler.on('conversation.*', (event: BackendEvent) => {
      console.log('Conversation event:', event.event_type);

      switch (event.event_type) {
        case 'conversation.agentresponse':
          // 创建智能体思考消息
          const thoughtMessage = createMessageFromEvent(event);
          thoughtMessage.content.result = event.data.response; // AI的思考内容
          thoughtMessage.content.response_type = event.data.response_type; // thought
          setMessages(prev => [...prev, thoughtMessage]);
          console.log('💭 AI思考内容:', event.data.response);
          break;
      }
    });

    // 监听流式输出事件
    eventHandler.on('stream.*', (event: BackendEvent) => {
      console.log('Stream event:', event.event_type);
    });

    // 监听系统事件
    eventHandler.on('system.*', (event: BackendEvent) => {
      console.log('System event:', event.event_type);

      switch (event.event_type) {
        case 'system.interrupt_acknowledged':
          setTaskStatus('paused');
          setAgentStatus('idle');
          console.log('⏸️ 用户中断已确认，任务暂停');
          break;
        case 'system.user_input_required':
          setWaitingForInput(true);
          setInputPrompt(event.data.prompt || '请输入信息');
          setAgentStatus('waiting');
          console.log('⏳ 等待用户输入:', event.data.prompt);
          break;
        case 'system.user_input_received':
          setWaitingForInput(false);
          setInputPrompt('');
          setAgentStatus('thinking');
          console.log('📝 用户输入已接收，继续执行');
          break;
        case 'system.task_started':
          setTaskStatus('running');
          setAgentStatus('thinking');
          console.log('🚀 任务开始执行');
          break;
        case 'system.task_completed':
          setTaskStatus('completed');
          setAgentStatus('idle');
          console.log('🎉 任务执行完成');
          break;
      }
    });
  };

  // 重置任务状态
  const resetTaskState = () => {
    setTaskStatus('idle');
    setAgentStatus('idle');
    setCurrentStep(0);
    setCurrentTool('');
    setWaitingForInput(false);
    setInputPrompt('');
    console.log('🔄 任务状态已重置');
  };

  // 提供发送事件的方法
  const sendUserInterrupt = () => {
    if (eventSenderRef.current && taskId) {
      eventSenderRef.current.sendUserInterrupt(taskId, 'user_requested').catch(error => console.error('Failed to send user interrupt:', error));
    } else {
      console.warn('Cannot send interrupt: eventSender or taskId missing');
    }
  };

  const sendUserInput = (message: string) => {
    if (eventSenderRef.current && taskId) {
      eventSenderRef.current.sendUserInput(taskId, message).catch(error => console.error('Failed to send user input:', error));
    } else {
      console.warn('Cannot send input: eventSender or taskId missing');
    }
  };

  const sendUIInteraction = (action: string, target: string, data: any = {}) => {
    if (eventSenderRef.current && taskId) {
      eventSenderRef.current.sendUIInteraction(taskId, action, target, data).catch(error => console.error('Failed to send UI interaction:', error));
    } else {
      console.warn('Cannot send UI interaction: eventSender or taskId missing');
    }
  };

  return {
    messages,
    stream: streamRef,
    // 任务状态
    taskStatus,
    agentStatus,
    currentStep,
    currentTool,
    waitingForInput,
    inputPrompt,
    // 导出事件发送方法
    sendUserInterrupt,
    sendUserInput,
    sendUIInteraction,
    resetTaskState,
    eventSender: eventSenderRef.current,
    eventHandler: eventHandlerRef.current,
  };
};

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const {
    messages,
    taskStatus,
    agentStatus,
    currentStep,
    currentTool,
    waitingForInput,
    inputPrompt,
    sendUserInterrupt,
    sendUserInput,
    sendUIInteraction,
    resetTaskState,
  } = useConversation(taskId);

  return (
    <div className="flex h-full gap-2 p-4">
      {/* Left: Chat Messages */}
      <div className="flex w-full flex-col overflow-auto">
        {/* 任务状态栏 */}
        <div className="mb-4 rounded-lg border bg-white p-3 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-700">任务状态</h3>
            <div
              className={`rounded-full px-2 py-1 text-xs font-medium ${
                taskStatus === 'idle'
                  ? 'bg-gray-100 text-gray-600'
                  : taskStatus === 'running'
                    ? 'bg-blue-100 text-blue-600'
                    : taskStatus === 'paused'
                      ? 'bg-yellow-100 text-yellow-600'
                      : taskStatus === 'completed'
                        ? 'bg-green-100 text-green-600'
                        : taskStatus === 'error'
                          ? 'bg-red-100 text-red-600'
                          : 'bg-gray-100 text-gray-600'
              }`}
            >
              {taskStatus === 'idle'
                ? '空闲'
                : taskStatus === 'running'
                  ? '运行中'
                  : taskStatus === 'paused'
                    ? '已暂停'
                    : taskStatus === 'completed'
                      ? '已完成'
                      : taskStatus === 'error'
                        ? '错误'
                        : '未知'}
            </div>
          </div>

          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <div className="flex items-center space-x-1">
              <span>{agentStatus === 'thinking' ? '🤔' : agentStatus === 'acting' ? '⚡' : agentStatus === 'waiting' ? '⏳' : '💤'}</span>
              <span>
                {agentStatus === 'thinking' ? '思考中' : agentStatus === 'acting' ? '执行中' : agentStatus === 'waiting' ? '等待输入' : '空闲'}
              </span>
            </div>

            {currentStep > 0 && (
              <div className="flex items-center space-x-1">
                <span>📋</span>
                <span>步骤: {currentStep}</span>
              </div>
            )}

            {currentTool && (
              <div className="flex items-center space-x-1">
                <span>🔧</span>
                <span>工具: {currentTool}</span>
                <div className="h-2 w-2 animate-pulse rounded-full bg-blue-500"></div>
              </div>
            )}
          </div>

          {waitingForInput && inputPrompt && (
            <div className="mt-2 rounded border border-yellow-200 bg-yellow-50 p-2 text-sm">
              <span className="font-medium text-yellow-800">等待输入: </span>
              <span className="text-yellow-700">{inputPrompt}</span>
            </div>
          )}
        </div>

        {/* 控制按钮 */}
        <div className="mb-4 flex gap-2 rounded bg-gray-100 p-2">
          <button
            onClick={() => sendUserInterrupt()}
            disabled={taskStatus !== 'running'}
            className={`rounded px-3 py-1 text-sm text-white ${
              taskStatus === 'running' ? 'bg-red-500 hover:bg-red-600' : 'cursor-not-allowed bg-gray-400'
            }`}
          >
            {taskStatus === 'running' ? '暂停任务' : '中断事件'}
          </button>
          <button onClick={() => sendUserInput('测试用户输入')} className="rounded bg-blue-500 px-3 py-1 text-sm text-white hover:bg-blue-600">
            发送用户输入
          </button>
          <button
            onClick={() => sendUIInteraction('click', 'test_button', { test: true })}
            className="rounded bg-green-500 px-3 py-1 text-sm text-white hover:bg-green-600"
          >
            UI交互事件
          </button>

          {(taskStatus === 'completed' || taskStatus === 'error') && (
            <button onClick={resetTaskState} className="rounded bg-gray-500 px-3 py-1 text-sm text-white hover:bg-gray-600">
              重置状态
            </button>
          )}
        </div>

        <ChatMessages messages={messages} />
      </div>

      {/* Right: Terminal Preview */}
      <ChatPreview taskId={taskId || ''} messages={messages} />
    </div>
  );
};

export default TaskDetailPage;
