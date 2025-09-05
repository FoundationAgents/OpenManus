import React from 'react';
import { TaskState } from '@/hooks/useTaskState';

interface TaskStatusPanelProps {
  taskState: TaskState;
  onInterrupt: () => void;
  onResume?: () => void;
  onReset?: () => void;
}

export const TaskStatusPanel: React.FC<TaskStatusPanelProps> = ({
  taskState,
  onInterrupt,
  onResume,
  onReset
}) => {
  const getStatusColor = (status: TaskState['status']) => {
    switch (status) {
      case 'idle': return 'bg-gray-500';
      case 'running': return 'bg-blue-500';
      case 'paused': return 'bg-yellow-500';
      case 'completed': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getAgentStatusIcon = (agentStatus: TaskState['agentStatus']) => {
    switch (agentStatus) {
      case 'thinking': return '🤔';
      case 'acting': return '⚡';
      case 'waiting': return '⏳';
      default: return '💤';
    }
  };

  const getStatusText = (status: TaskState['status']) => {
    switch (status) {
      case 'idle': return '空闲';
      case 'running': return '运行中';
      case 'paused': return '已暂停';
      case 'completed': return '已完成';
      case 'error': return '错误';
      default: return '未知';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 space-y-4">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">任务状态</h3>
        <div className={`px-3 py-1 rounded-full text-white text-sm ${getStatusColor(taskState.status)}`}>
          {getStatusText(taskState.status)}
        </div>
      </div>

      {/* 进度条 */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-gray-600">
          <span>进度</span>
          <span>{taskState.progress.percentage.toFixed(0)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${taskState.progress.percentage}%` }}
          />
        </div>
        <p className="text-sm text-gray-600">{taskState.progress.message}</p>
      </div>

      {/* 智能体状态 */}
      <div className="flex items-center space-x-3">
        <span className="text-2xl">{getAgentStatusIcon(taskState.agentStatus)}</span>
        <div>
          <p className="text-sm font-medium text-gray-800">智能体状态</p>
          <p className="text-sm text-gray-600">
            {taskState.agentStatus === 'thinking' && '思考中...'}
            {taskState.agentStatus === 'acting' && '执行中...'}
            {taskState.agentStatus === 'waiting' && '等待输入...'}
            {taskState.agentStatus === 'idle' && '空闲'}
          </p>
        </div>
      </div>

      {/* 步骤信息 */}
      {taskState.currentStep > 0 && (
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">当前步骤:</span>
          <span className="font-medium">
            {taskState.currentStep}
            {taskState.totalSteps && ` / ${taskState.totalSteps}`}
          </span>
        </div>
      )}

      {/* 工具执行状态 */}
      {taskState.currentTool && (
        <div className="bg-gray-50 rounded p-3">
          <p className="text-sm font-medium text-gray-800">当前工具</p>
          <p className="text-sm text-gray-600">{taskState.currentTool}</p>
          <div className="flex items-center mt-1">
            <div className={`w-2 h-2 rounded-full mr-2 ${
              taskState.toolStatus === 'executing' ? 'bg-blue-500 animate-pulse' :
              taskState.toolStatus === 'completed' ? 'bg-green-500' :
              taskState.toolStatus === 'error' ? 'bg-red-500' : 'bg-gray-400'
            }`} />
            <span className="text-xs text-gray-500">
              {taskState.toolStatus === 'executing' && '执行中'}
              {taskState.toolStatus === 'completed' && '已完成'}
              {taskState.toolStatus === 'error' && '执行失败'}
              {taskState.toolStatus === 'idle' && '空闲'}
            </span>
          </div>
        </div>
      )}

      {/* 错误信息 */}
      {taskState.error && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-sm font-medium text-red-800">错误信息</p>
          <p className="text-sm text-red-600">{taskState.error}</p>
        </div>
      )}

      {/* 用户输入提示 */}
      {taskState.waitingForInput && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-sm font-medium text-yellow-800">等待用户输入</p>
          <p className="text-sm text-yellow-600">{taskState.inputPrompt}</p>
        </div>
      )}

      {/* 控制按钮 */}
      <div className="flex space-x-2 pt-2 border-t">
        {taskState.status === 'running' && (
          <button
            onClick={onInterrupt}
            className="flex-1 px-3 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
          >
            暂停任务
          </button>
        )}
        
        {taskState.status === 'paused' && onResume && (
          <button
            onClick={onResume}
            className="flex-1 px-3 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
          >
            继续任务
          </button>
        )}
        
        {(taskState.status === 'completed' || taskState.status === 'error') && onReset && (
          <button
            onClick={onReset}
            className="flex-1 px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors"
          >
            重置任务
          </button>
        )}
      </div>
    </div>
  );
};
