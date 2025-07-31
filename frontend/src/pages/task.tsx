import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { ManusMessageSocket, type ManusMessage, type Message, type MessageType } from '@/libs/chat-messages';
import { EventSender } from '@/libs/event-sender';
import { FrontendEventHandler, type BackendEvent } from '@/libs/event-handler';
import { type WebSocketState } from '@/libs/websocket/types';
import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ChatInput } from '@/components/features/chat/input';

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

  const createAssistantMessageFromEvent = (event: BackendEvent): Message => {
    if (event.event_type === 'tool.toolexecution') {
    }
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

  const createUserMessageFromEvent = (event: BackendEvent): Message => {
    return {
      index: Date.now() + Math.random(), // 使用时间戳+随机数确保唯一性
      role: 'user' as const,
      content: event.data.message,
      type: 'conversation.userinput',
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
          const startMessage = createAssistantMessageFromEvent(event);
          setMessages(prev => [...prev, startMessage]);
          break;

        case 'agent.agentstepcomplete':
          // 步骤完成后，检查是否还有更多步骤
          setAgentStatus('idle');
          console.log(`✅ 步骤 ${currentStep} 完成`);

          // 创建步骤完成消息
          const completeMessage = createAssistantMessageFromEvent(event);
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
          const taskCompleteMessage = createAssistantMessageFromEvent(event);
          setMessages(prev => [...prev, taskCompleteMessage]);
          break;

        case 'agent.error':
          setTaskStatus('error');
          setAgentStatus('idle');
          console.log('❌ 智能体执行出错');

          // 创建错误消息
          const errorMessage = createAssistantMessageFromEvent(event);
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
          const toolStartMessage = createAssistantMessageFromEvent(event);
          toolStartMessage.content.result = `🔧 开始执行工具: ${event.data.tool_name}`;
          setMessages(prev => [...prev, toolStartMessage]);
          break;

        case 'tool.toolresult':
          const toolName = currentTool || event.data.tool_name;
          console.log(`✅ 工具执行完成: ${toolName}`);

          // 创建工具完成消息
          const toolCompleteMessage = createAssistantMessageFromEvent(event);
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
      }
    });

    // 监听对话事件
    eventHandler.on('conversation.*', (event: BackendEvent) => {
      console.log('Conversation event:', event.event_type);

      switch (event.event_type) {
        case 'conversation.userinput':
          // 用户输入被接收，创建用户消息并重置状态为思考中
          setMessages(prev => [...prev, createUserMessageFromEvent(event)]);
          setAgentStatus('thinking');
          setTaskStatus('running');
          console.log('📝 用户输入已接收，开始处理');
          break;
        case 'conversation.agentresponse':
          // 创建智能体思考消息
          const thoughtMessage = createAssistantMessageFromEvent(event);
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

  // 提供发送事件的方法
  const sendUserInterrupt = async () => {
    if (eventSenderRef.current && taskId) {
      await eventSenderRef.current.sendUserInterrupt(taskId, 'user_requested').catch(error => console.error('Failed to send user interrupt:', error));
    } else {
      console.warn('Cannot send interrupt: eventSender or taskId missing');
    }
  };

  const sendUserInput = async (message: string) => {
    if (eventSenderRef.current && taskId) {
      // 设置状态为思考中，表示正在处理用户输入
      setAgentStatus('thinking');
      setTaskStatus('running');

      await eventSenderRef.current.sendUserInput(taskId, message).catch(error => {
        console.error('Failed to send user input:', error);
        // 如果发送失败，重置状态
        setAgentStatus('idle');
        setTaskStatus('completed');
      });
    } else {
      console.warn('Cannot send input: eventSender or taskId missing');
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
    eventSender: eventSenderRef.current,
    eventHandler: eventHandlerRef.current,
  };
};

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const { messages, taskStatus, agentStatus, sendUserInterrupt, sendUserInput } = useConversation(taskId);

  // 计算输入框状态
  const getInputStatus = () => {
    if (agentStatus === 'thinking' || agentStatus === 'acting') {
      return 'thinking';
    }
    // 允许在任何非思考状态下输入，包括完成状态（支持继续对话）
    return 'idle';
  };

  return (
    <div className="flex h-full gap-2 p-4">
      {/* Left: Chat Messages */}
      <div className="flex h-full w-1/2 flex-col overflow-hidden">
        <ChatMessages messages={messages} className="flex-1 overflow-auto" />
        <ChatInput
          status={getInputStatus()}
          onSubmit={value => sendUserInput(value.prompt)}
          onTerminate={() => sendUserInterrupt()}
          taskId={taskId}
          className="p-4"
        />
      </div>

      {/* Right: Terminal Preview */}
      <ChatPreview taskId={taskId || ''} messages={messages} className="w-1/2" />
    </div>
  );
};

export default TaskDetailPage;
