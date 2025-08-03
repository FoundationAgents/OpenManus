/**
 * 前端事件发送器
 * 用于向后端发送事件
 */

import { WebSocketAdapter, type WebSocketMessage } from './websocket';

export interface EventData {
  [key: string]: any;
}

export interface FrontendEvent {
  type: 'event';
  event_type: string;
  event_id: string;
  data: EventData;
  conversation_id?: string;
  timestamp: string;
}

export class EventSender {
  private websocket: WebSocketAdapter<any>;

  constructor(websocket: WebSocketAdapter<any>) {
    this.websocket = websocket;
  }

  /**
   * 发送事件到后端
   * @param eventType 事件类型，如 'user.interrupt', 'user.input'
   * @param data 事件数据
   * @param conversationId 对话ID（可选）
   * @returns Promise<void>
   */
  async sendEvent(
    eventType: string,
    data: EventData = {},
    conversationId?: string
  ): Promise<void> {
    if (!this.websocket.isConnected) {
      console.warn('WebSocket not connected, cannot send event');
      throw new Error('WebSocket not connected');
    }

    const event: FrontendEvent = {
      type: 'event',
      event_type: eventType,
      event_id: this.generateUUID(),
      data: {
        ...data,
        conversation_id: conversationId
      },
      conversation_id: conversationId,
      timestamp: new Date().toISOString()
    };

    try {
      this.websocket.send(event);
      console.log(`Event sent: ${eventType}`, event);
    } catch (error) {
      console.error(`Failed to send event ${eventType}:`, error);
      throw error;
    }
  }

  /**
   * 发送用户中断事件
   * @param conversationId 对话ID
   * @param reason 中断原因
   */
  async sendUserInterrupt(conversationId: string, reason: string = 'user_requested'): Promise<void> {
    await this.sendEvent('user.interrupt', {
      reason: reason
    }, conversationId);
  }

  /**
   * 发送用户输入事件
   * @param conversationId 对话ID
   * @param message 用户输入的消息
   */
  async sendUserInput(conversationId: string, message: string): Promise<void> {
    await this.sendEvent('user.input', {
      message: message
    }, conversationId);
  }

  /**
   * 发送UI交互事件
   * @param conversationId 对话ID
   * @param action 交互动作
   * @param target 交互目标
   * @param data 额外数据
   */
  async sendUIInteraction(
    conversationId: string,
    action: string,
    target: string,
    data: EventData = {}
  ): Promise<void> {
    await this.sendEvent('ui.interaction', {
      action: action,
      target: target,
      ...data
    }, conversationId);
  }

  /**
   * 发送自定义事件
   * @param eventType 事件类型
   * @param data 事件数据
   * @param conversationId 对话ID（可选）
   */
  async sendCustomEvent(
    eventType: string,
    data: EventData,
    conversationId?: string
  ): Promise<void> {
    await this.sendEvent(eventType, data, conversationId);
  }

  /**
   * 检查WebSocket连接状态
   * @returns boolean
   */
  isConnected(): boolean {
    return this.websocket.isConnected;
  }

  /**
   * 获取WebSocket连接状态
   * @returns WebSocket状态信息
   */
  getConnectionStatus() {
    return this.websocket.status;
  }

  /**
   * 生成UUID
   * @returns string
   */
  private generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = Math.random() * 16 | 0;
      const v = c == 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
}

// 导出类型
export type { FrontendEvent, EventData };
