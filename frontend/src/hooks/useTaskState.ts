import { useState, useCallback } from 'react';
import { BackendEvent } from '@/libs/event-handler';

// 任务状态类型
export interface TaskState {
  // 基本状态
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  
  // 智能体状态
  agentStatus: 'idle' | 'thinking' | 'acting' | 'waiting';
  currentStep: number;
  totalSteps?: number;
  
  // 工具执行状态
  currentTool?: string;
  toolStatus: 'idle' | 'executing' | 'completed' | 'error';
  
  // 用户交互状态
  waitingForInput: boolean;
  inputPrompt?: string;
  
  // 错误状态
  error?: string;
  
  // 进度信息
  progress: {
    percentage: number;
    message: string;
  };
}

// 初始状态
const initialState: TaskState = {
  status: 'idle',
  agentStatus: 'idle',
  currentStep: 0,
  toolStatus: 'idle',
  waitingForInput: false,
  progress: {
    percentage: 0,
    message: '准备中...'
  }
};

/**
 * 基于事件系统的任务状态管理Hook
 */
export const useTaskState = () => {
  const [state, setState] = useState<TaskState>(initialState);

  // 处理智能体事件
  const handleAgentEvent = useCallback((event: BackendEvent) => {
    setState(prev => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'agent.agentstepstart':
          newState.status = 'running';
          newState.agentStatus = 'thinking';
          newState.currentStep = event.data.step_number || prev.currentStep + 1;
          newState.progress = {
            percentage: Math.min((newState.currentStep / (prev.totalSteps || 10)) * 100, 90),
            message: `执行步骤 ${newState.currentStep}...`
          };
          break;
          
        case 'agent.agentstepcomplete':
          newState.agentStatus = 'idle';
          newState.progress = {
            percentage: Math.min(((newState.currentStep + 1) / (prev.totalSteps || 10)) * 100, 95),
            message: `步骤 ${newState.currentStep} 完成`
          };
          break;
          
        case 'agent.task_completed':
          newState.status = 'completed';
          newState.agentStatus = 'idle';
          newState.progress = {
            percentage: 100,
            message: '任务完成'
          };
          break;
          
        case 'agent.error':
          newState.status = 'error';
          newState.agentStatus = 'idle';
          newState.error = event.data.message || '智能体执行出错';
          break;
      }
      
      return newState;
    });
  }, []);

  // 处理工具事件
  const handleToolEvent = useCallback((event: BackendEvent) => {
    setState(prev => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'tool.toolexecution':
          newState.currentTool = event.data.tool_name;
          newState.toolStatus = 'executing';
          newState.agentStatus = 'acting';
          newState.progress = {
            ...prev.progress,
            message: `执行工具: ${event.data.tool_name}`
          };
          break;
          
        case 'tool.execution.complete':
          newState.toolStatus = 'completed';
          newState.agentStatus = 'thinking';
          newState.progress = {
            ...prev.progress,
            message: `工具 ${prev.currentTool} 执行完成`
          };
          break;
          
        case 'tool.execution.error':
          newState.toolStatus = 'error';
          newState.error = event.data.error || '工具执行失败';
          break;
      }
      
      return newState;
    });
  }, []);

  // 处理系统事件
  const handleSystemEvent = useCallback((event: BackendEvent) => {
    setState(prev => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'system.interrupt_acknowledged':
          newState.status = 'paused';
          newState.agentStatus = 'idle';
          newState.progress = {
            ...prev.progress,
            message: '任务已暂停'
          };
          break;
          
        case 'system.user_input_required':
          newState.waitingForInput = true;
          newState.inputPrompt = event.data.prompt || '请输入信息';
          newState.agentStatus = 'waiting';
          break;
          
        case 'system.user_input_received':
          newState.waitingForInput = false;
          newState.inputPrompt = undefined;
          newState.agentStatus = 'thinking';
          break;
      }
      
      return newState;
    });
  }, []);

  // 重置状态
  const resetState = useCallback(() => {
    setState(initialState);
  }, []);

  return {
    state,
    handlers: {
      handleAgentEvent,
      handleToolEvent,
      handleSystemEvent
    },
    actions: {
      resetState
    }
  };
};
