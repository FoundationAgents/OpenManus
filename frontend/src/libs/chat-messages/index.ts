
import { WebSocketAdapter } from '@/libs/websocket';
import type { WebSocketState } from '@/libs/websocket';

export type MessageType = 'agent.agentstepstart' | 'agent.agentstepcomplete';

export type Message<T = any> = {
  index?: number;
  role: 'user' | 'assistant';
  createdAt?: Date;
  type?: MessageType;
  step?: number;
  content: T;
};

/**
 * WebSocket消息类型
 */
export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
}

/**
 * Manus WebSocket消息类型
 */
export interface ManusMessage extends WebSocketMessage {
  type: 'connection_established' | 'stream_start' | 'stream_end' | 'processing_start' | 'chat_message' | 'error' | 'ping' | 'pong' | 'agent_event' | 'session_status';
  session_id?: string;
  connection_id?: string;
  content?: string;
  error?: string;
  timestamp?: string;
  // Agent 事件相关字段
  event_type?: string;
  step?: number;
  data?: any;
  // 会话状态相关字段
  status?: string;
  progress?: number;
  current_step?: number;
}

/**
 * 消息流状态
 */
export type StreamStatus = 'idle' | 'connecting' | 'connected' | 'processing' | 'completed' | 'error';

/**
 * 事件处理器类型
 */
export type MessageStreamHandler = (message: Message) => void;
export type StreamErrorHandler = (error: Error) => void;
export type StreamStatusHandler = (status: StreamStatus) => void;
export type RawMessageHandler<T = WebSocketMessage> = (message: T) => void;

/**
 * 消息流配置
 */
export interface MessageStreamConfig {
  url: string;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  pingInterval?: number;
  connectionTimeout?: number;
  autoReconnect?: boolean;
  enablePing?: boolean;
  enableLogging?: boolean;
  // Manus特定配置
  sessionId?: string;
  baseUrl?: string;

  // 消息流配置
  onMessage?: MessageStreamHandler;
  onError?: StreamErrorHandler;
  onStatus?: StreamStatusHandler;
}

/**
 * 聊天消息流管理器
 * 基于WebSocket标准库，提供聊天消息的流式处理功能
 */
export class ManusMessageSocket<T extends WebSocketMessage = WebSocketMessage> {
  private ws: WebSocketAdapter<T>;
  private messageIndex = 0;

  // 事件处理器集合
  private messageHandlers: Set<MessageStreamHandler> = new Set();
  private errorHandlers: Set<StreamErrorHandler> = new Set();
  private statusHandlers: Set<StreamStatusHandler> = new Set();
  private rawMessageHandlers: Set<RawMessageHandler<T>> = new Set();

  constructor(config: MessageStreamConfig) {
    // 创建WebSocket管理器
    this.ws = new WebSocketAdapter<T>({
      reconnectAttempts: config.reconnectAttempts ?? 3,
      reconnectDelay: config.reconnectDelay ?? 5000,
      pingInterval: config.pingInterval ?? 30000,
      connectionTimeout: config.connectionTimeout ?? 10000
    }, {
      autoReconnect: config.autoReconnect ?? true,
      enablePing: config.enablePing ?? true,
      enableLogging: config.enableLogging ?? false
    });

    if (config.onMessage) {
      this.onMessage(config.onMessage);
    }
    if (config.onError) {
      this.onError(config.onError);
    }
    this.setupEventHandlers();
  }

  /**
   * 连接消息流
   */
  async connect(url: string): Promise<void> {
    return this.ws.connect(url);
  }

  /**
   * 断开消息流
   */
  disconnect(): void {
    this.ws.disconnect();
  }

  /**
   * 发送消息
   */
  send(message: string | object): void {
    this.ws.send(message);
  }

  // ==================== 事件监听器管理 ====================

  /**
   * 注册消息处理器（处理转换后的Message对象）
   */
  onMessage(handler: MessageStreamHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /**
   * 注册错误处理器
   */
  onError(handler: StreamErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  private setupEventHandlers(): void {
    // 监听WebSocket层的消息
    this.ws.onMessage((rawMessage: T) => {
      // 先处理原始消息
      this.notifyRawMessageHandlers(rawMessage);

      // 转换为Message对象并处理
      const message = this.transformMessage(rawMessage);
      if (message) {
        this.notifyMessageHandlers(message);
      }
    });

    // 监听WebSocket层的错误
    this.ws.onError((error: Error) => {
      this.notifyErrorHandlers(error);
    });

    // 监听WebSocket层的状态变化
    this.ws.onState((state: WebSocketState) => {
      const streamStatus = this.mapWebSocketStateToStreamStatus(state);
      this.notifyStatusHandlers(streamStatus);
    });
  }

  /**
   * 将WebSocket消息转换为Message对象
   * 支持通用消息和Manus特定消息的转换
   */
  private transformMessage(rawMessage: T): Message | null {
    try {
      // 检查是否为Manus agent_event类型消息
      if ('type' in rawMessage && rawMessage.type === 'agent_event') {
        const manusMessage = rawMessage as ManusMessage;
        return {
          index: this.messageIndex++,
          role: 'assistant' as const,
          content: manusMessage.content || manusMessage.data || {},
          createdAt: manusMessage.timestamp ? new Date(manusMessage.timestamp) : new Date(),
          type: manusMessage.event_type as any,
          step: manusMessage.step
        };
      }

      return null;
    } catch (error) {
      console.error('消息转换失败:', error);
      return null;
    }
  }

  private notifyMessageHandlers(message: Message): void {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('消息处理器错误:', error);
      }
    });
  }

  private notifyRawMessageHandlers(rawMessage: T): void {
    this.rawMessageHandlers.forEach(handler => {
      try {
        handler(rawMessage);
      } catch (error) {
        console.error('原始消息处理器错误:', error);
      }
    });
  }

  private notifyErrorHandlers(error: Error): void {
    this.errorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (err) {
        console.error('错误处理器错误:', err);
      }
    });
  }

  private notifyStatusHandlers(status: StreamStatus): void {
    this.statusHandlers.forEach(handler => {
      try {
        handler(status);
      } catch (error) {
        console.error('状态处理器错误:', error);
      }
    });
  }

  private mapWebSocketStateToStreamStatus(wsState: WebSocketState): StreamStatus {
    switch (wsState) {
      case 'idle':
        return 'idle';
      case 'connecting':
      case 'reconnecting':
        return 'connecting';
      case 'connected':
        return 'connected';
      case 'error':
        return 'error';
      default:
        return 'idle';
    }
  }
}
