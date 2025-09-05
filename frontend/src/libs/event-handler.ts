/**
 * 前端事件处理器
 * 用于处理从后端接收的事件
 */

export interface BackendEvent {
  type: 'event';
  event_type: string;
  event_id: string;
  data: Record<string, any>;
  timestamp: string;
  source?: string;
}

export type EventHandler = (event: BackendEvent) => void;

export class FrontendEventHandler {
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private wildcardHandlers: Map<string, Set<EventHandler>> = new Map();

  /**
   * 注册事件处理器
   * @param eventType 事件类型或模式，支持通配符如 'agent.*'
   * @param handler 事件处理函数
   * @returns 取消订阅函数
   */
  on(eventType: string, handler: EventHandler): () => void {
    // 检查是否是通配符模式
    if (eventType.includes('*')) {
      if (!this.wildcardHandlers.has(eventType)) {
        this.wildcardHandlers.set(eventType, new Set());
      }
      this.wildcardHandlers.get(eventType)!.add(handler);

      // 返回取消订阅函数
      return () => {
        const handlers = this.wildcardHandlers.get(eventType);
        if (handlers) {
          handlers.delete(handler);
          if (handlers.size === 0) {
            this.wildcardHandlers.delete(eventType);
          }
        }
      };
    } else {
      // 精确匹配
      if (!this.handlers.has(eventType)) {
        this.handlers.set(eventType, new Set());
      }
      this.handlers.get(eventType)!.add(handler);

      // 返回取消订阅函数
      return () => {
        const handlers = this.handlers.get(eventType);
        if (handlers) {
          handlers.delete(handler);
          if (handlers.size === 0) {
            this.handlers.delete(eventType);
          }
        }
      };
    }
  }

  /**
   * 注册一次性事件处理器
   * @param eventType 事件类型
   * @param handler 事件处理函数
   * @returns 取消订阅函数
   */
  once(eventType: string, handler: EventHandler): () => void {
    const wrappedHandler = (event: BackendEvent) => {
      handler(event);
      unsubscribe(); // 执行后自动取消订阅
    };

    const unsubscribe = this.on(eventType, wrappedHandler);
    return unsubscribe;
  }

  /**
   * 移除事件处理器
   * @param eventType 事件类型
   * @param handler 要移除的处理器（可选，如果不提供则移除该类型的所有处理器）
   */
  off(eventType: string, handler?: EventHandler): void {
    if (handler) {
      // 移除特定处理器
      const handlers = this.handlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(eventType);
        }
      }

      const wildcardHandlers = this.wildcardHandlers.get(eventType);
      if (wildcardHandlers) {
        wildcardHandlers.delete(handler);
        if (wildcardHandlers.size === 0) {
          this.wildcardHandlers.delete(eventType);
        }
      }
    } else {
      // 移除该类型的所有处理器
      this.handlers.delete(eventType);
      this.wildcardHandlers.delete(eventType);
    }
  }

  /**
   * 处理接收到的事件
   * @param event 后端发送的事件
   */
  handleEvent(event: BackendEvent): void {
    if (!event || !event.event_type) {
      console.warn('Invalid event received:', event);
      return;
    }

    const eventType = event.event_type;
    let handlerCount = 0;

    try {
      // 处理精确匹配的处理器
      const exactHandlers = this.handlers.get(eventType);
      if (exactHandlers) {
        exactHandlers.forEach(handler => {
          try {
            handler(event);
            handlerCount++;
          } catch (error) {
            console.error(`Error in event handler for ${eventType}:`, error);
          }
        });
      }

      // 处理通配符匹配的处理器
      this.wildcardHandlers.forEach((handlers, pattern) => {
        if (this.matchPattern(eventType, pattern)) {
          handlers.forEach(handler => {
            try {
              handler(event);
              handlerCount++;
            } catch (error) {
              console.error(`Error in wildcard event handler for ${pattern}:`, error);
            }
          });
        }
      });

      console.log(`Event ${eventType} processed by ${handlerCount} handlers`);

    } catch (error) {
      console.error(`Error processing event ${eventType}:`, error);
    }
  }

  /**
   * 检查事件类型是否匹配模式
   * @param eventType 事件类型
   * @param pattern 匹配模式，支持 * 通配符
   * @returns boolean
   */
  private matchPattern(eventType: string, pattern: string): boolean {
    if (pattern === eventType) {
      return true;
    }

    if (pattern.includes('*')) {
      // 简单的通配符匹配
      const regexPattern = pattern
        .replace(/\./g, '\\.')  // 转义点号
        .replace(/\*/g, '.*');  // * 替换为 .*

      const regex = new RegExp(`^${regexPattern}$`);
      return regex.test(eventType);
    }

    return false;
  }

  /**
   * 获取已注册的事件类型列表
   * @returns string[]
   */
  getRegisteredEventTypes(): string[] {
    const exactTypes = Array.from(this.handlers.keys());
    const wildcardTypes = Array.from(this.wildcardHandlers.keys());
    return [...exactTypes, ...wildcardTypes];
  }

  /**
   * 获取指定事件类型的处理器数量
   * @param eventType 事件类型
   * @returns number
   */
  getHandlerCount(eventType: string): number {
    const exactCount = this.handlers.get(eventType)?.size || 0;
    const wildcardCount = this.wildcardHandlers.get(eventType)?.size || 0;
    return exactCount + wildcardCount;
  }

  /**
   * 清除所有事件处理器
   */
  clear(): void {
    this.handlers.clear();
    this.wildcardHandlers.clear();
  }

  /**
   * 清除指定事件类型的所有处理器
   * @param eventType 事件类型或模式
   */
  clearEventType(eventType: string): void {
    if (eventType.includes('*')) {
      this.wildcardHandlers.delete(eventType);
    } else {
      this.handlers.delete(eventType);
    }
    console.log(`Cleared handlers for event type: ${eventType}`);
  }

  /**
   * 获取统计信息
   * @returns 处理器统计信息
   */
  getStats() {
    return {
      exactHandlers: this.handlers.size,
      wildcardHandlers: this.wildcardHandlers.size,
      totalEventTypes: this.getRegisteredEventTypes().length,
      totalHandlers: Array.from(this.handlers.values()).reduce((sum, set) => sum + set.size, 0) +
        Array.from(this.wildcardHandlers.values()).reduce((sum, set) => sum + set.size, 0)
    };
  }
}

// 便捷的事件处理器工厂函数
export function createEventHandler(): FrontendEventHandler {
  return new FrontendEventHandler();
}

// 导出类型
export type { BackendEvent, EventHandler };
