// WebSocket 通用类型定义

export interface WebSocketConfig {
  protocols?: string | string[];
  reconnectAttempts?: number;
  reconnectDelay?: number;
  pingInterval?: number;
  connectionTimeout?: number;
}

// 内部使用的完整配置类型
export interface InternalWebSocketConfig {
  protocols?: string | string[];
  reconnectAttempts: number;
  reconnectDelay: number;
  pingInterval: number;
  connectionTimeout: number;
}

export type WebSocketState = 'idle' | 'connecting' | 'connected' | 'disconnecting' | 'error' | 'reconnecting';

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: string;
}

export interface ConnectionOptions {
  autoReconnect?: boolean;
  enablePing?: boolean;
  enableLogging?: boolean;
}

// 事件处理器类型
export type MessageHandler<T = WebSocketMessage> = (message: T) => void;
export type ErrorHandler = (error: Error) => void;
export type StateHandler = (state: WebSocketState) => void;

// WebSocket连接状态详情
export interface ConnectionState {
  state: WebSocketState;
  isConnected: boolean;
  reconnectAttempts: number;
  lastError?: Error;
  connectedAt?: Date;
  disconnectedAt?: Date;
}
