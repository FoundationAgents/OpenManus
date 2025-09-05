// WebSocket 连接管理器
// 提供连接管理、消息处理、自动重连、心跳检测等功能

import type {
  WebSocketConfig,
  InternalWebSocketConfig,
  WebSocketState,
  WebSocketMessage,
  MessageHandler,
  ErrorHandler,
  StateHandler,
  ConnectionOptions,
  ConnectionState
} from './types';

/**
 * WebSocket 连接管理器
 * 提供连接管理、消息处理、自动重连、心跳检测等功能
 */
class WebSocketAdapter<T extends WebSocketMessage = WebSocketMessage> {
  private ws: WebSocket | null = null;
  private state: WebSocketState = 'idle';
  private config: InternalWebSocketConfig;
  private options: Required<ConnectionOptions>;

  // 事件处理器集合
  private messageHandlers: Set<MessageHandler<T>> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private stateHandlers: Set<StateHandler> = new Set();

  // 重连和心跳相关
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;
  private connectionTimer: NodeJS.Timeout | null = null;
  private currentReconnectAttempts = 0;

  // 连接状态详情
  private connectionState: ConnectionState = {
    state: 'idle',
    isConnected: false,
    reconnectAttempts: 0
  };

  constructor(config: WebSocketConfig, options: ConnectionOptions = {}) {
    this.config = {
      reconnectAttempts: 3,
      reconnectDelay: 5000,
      pingInterval: 30000,
      connectionTimeout: 10000,
      ...config
    };

    this.options = {
      autoReconnect: true,
      enablePing: true,
      enableLogging: false,
      ...options
    };
  }

  /**
   * 建立WebSocket连接
   */
  async connect(url: string): Promise<void> {
    if (this.state === 'connecting' || this.state === 'connected') {
      return;
    }

    this.setState('connecting');
    this.log('正在连接WebSocket...', url);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(url, this.config.protocols);

        // 设置连接超时
        this.connectionTimer = setTimeout(() => {
          if (this.ws?.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            const error = new Error('连接超时');
            this.handleError(error);
            reject(error);
          }
        }, this.config.connectionTimeout);

        this.ws.onopen = () => {
          this.clearConnectionTimer();
          this.currentReconnectAttempts = 0;
          this.connectionState.connectedAt = new Date();
          this.setState('connected');
          this.log('WebSocket连接已建立');

          if (this.options.enablePing) {
            this.startPing();
          }

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          this.clearTimers();
          this.connectionState.disconnectedAt = new Date();
          this.log(`WebSocket连接已关闭: ${event.code} ${event.reason}`);

          if (event.code === 1000) {
            // 正常关闭
            this.setState('idle');
          } else {
            // 异常关闭，尝试重连
            this.setState('error');
            if (this.options.autoReconnect) {
              this.scheduleReconnect(url);
            }
          }
        };

        this.ws.onerror = () => {
          this.clearConnectionTimer();
          this.log('WebSocket连接错误');
          const err = new Error('WebSocket连接错误');
          this.handleError(err);

          if (this.state === 'connecting') {
            reject(err);
          }
        };

      } catch (error) {
        this.clearConnectionTimer();
        const err = error instanceof Error ? error : new Error('连接失败');
        this.handleError(err);
        reject(err);
      }
    });
  }

  /**
   * 断开WebSocket连接
   */
  disconnect(): void {
    this.clearTimers();

    if (this.ws) {
      this.setState('disconnecting');
      this.ws.close(1000, '用户主动断开');
      this.ws = null;
    }

    this.setState('idle');
    this.log('WebSocket连接已断开');
  }

  /**
   * 发送消息
   */
  send(message: string | object): void {
    if (!this.isConnected) {
      throw new Error('WebSocket未连接');
    }

    const data = typeof message === 'string' ? message : JSON.stringify(message);
    this.ws!.send(data);
    this.log('发送消息:', data);
  }

  /**
   * 发送Ping消息
   */
  ping(): void {
    this.send({ type: 'ping' });
  }

  // ==================== 事件监听器管理 ====================

  /**
   * 注册消息处理器
   */
  onMessage(handler: MessageHandler<T>): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /**
   * 注册错误处理器
   */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  /**
   * 注册状态处理器
   */
  onState(handler: StateHandler): () => void {
    this.stateHandlers.add(handler);
    return () => this.stateHandlers.delete(handler);
  }

  // ==================== 状态查询 ====================

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * 获取当前状态
   */
  get currentState(): WebSocketState {
    return this.state;
  }

  /**
   * 获取连接状态详情
   */
  get status(): ConnectionState {
    return {
      ...this.connectionState,
      state: this.state,
      isConnected: this.isConnected
    };
  }

  // ==================== 私有方法 ====================

  private setState(newState: WebSocketState): void {
    const oldState = this.state;
    this.state = newState;
    this.connectionState.state = newState;

    this.log(`状态变更: ${oldState} -> ${newState}`);

    this.stateHandlers.forEach(handler => {
      try {
        handler(newState);
      } catch (error) {
        console.error('状态处理器错误:', error);
      }
    });
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: T = JSON.parse(event.data);
      this.log('收到消息:', message);

      // 处理特殊消息类型
      if (message.type === 'pong') {
        // 心跳响应，无需通知业务层
        return;
      }

      // 通知所有消息处理器
      this.messageHandlers.forEach(handler => {
        try {
          handler(message);
        } catch (error) {
          console.error('消息处理器错误:', error);
        }
      });

    } catch (error) {
      this.log('消息解析失败:', error);
      this.handleError(new Error('消息解析失败'));
    }
  }

  private handleError(error: Error): void {
    this.connectionState.lastError = error;
    this.log('错误:', error.message);

    this.errorHandlers.forEach(handler => {
      try {
        handler(error);
      } catch (err) {
        console.error('错误处理器错误:', err);
      }
    });
  }

  private scheduleReconnect(url: string): void {
    if (this.currentReconnectAttempts >= this.config.reconnectAttempts) {
      this.log('重连次数已达上限，停止重连');
      return;
    }

    this.currentReconnectAttempts++;
    this.connectionState.reconnectAttempts = this.currentReconnectAttempts;
    this.setState('reconnecting');

    this.log(`${this.config.reconnectDelay}ms后尝试第${this.currentReconnectAttempts}次重连`);

    this.reconnectTimer = setTimeout(() => {
      this.connect(url).catch((error) => {
        this.log('重连失败:', error.message);
        this.scheduleReconnect(url);
      });
    }, this.config.reconnectDelay);
  }

  private startPing(): void {
    this.pingTimer = setInterval(() => {
      if (this.isConnected) {
        this.ping();
      }
    }, this.config.pingInterval);
  }

  private clearTimers(): void {
    this.clearConnectionTimer();
    this.clearReconnectTimer();
    this.clearPingTimer();
  }

  private clearConnectionTimer(): void {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private log(...args: any[]): void {
    if (this.options.enableLogging) {
      console.log('[WebSocketAdapter]', ...args);
    }
  }
}

export { WebSocketAdapter };

export type {
  WebSocketConfig,
  InternalWebSocketConfig,
  WebSocketState,
  WebSocketMessage,
  MessageHandler,
  ErrorHandler,
  StateHandler,
  ConnectionOptions
} from './types';
