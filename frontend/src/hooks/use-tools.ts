import { create } from 'zustand';
import { useCallback, useEffect } from 'react';

// Mock types and functions
interface AgentTool {
  id: string;
  name: string;
  description?: string;
  type?: string;
}

// Mock function for listAgentTools
const listAgentTools = async () => {
  await new Promise(resolve => setTimeout(resolve, 500));
  return {
    data: [
      { id: 'file_operators', name: 'File Operators', description: 'File read and write tools' },
      { id: 'python_execute', name: 'Python Execute', description: 'Execute Python code' },
      { id: 'web_search', name: 'Web Search', description: 'Search the web' },
      { id: 'browser_use', name: 'Browser', description: 'Browser automation tool' },
      { id: 'bash', name: 'Bash', description: 'Execute system commands' },
      { id: 'search', name: 'Search', description: 'Search tools' },
      { id: 'mcp', name: 'MCP', description: 'Model Context Protocol tool' },
      { id: 'planning', name: 'Planning', description: 'Task planning and analysis' },
      { id: 'ask_human', name: 'Ask Human', description: 'Ask human for information' },
      { id: 'terminate', name: 'Terminate', description: 'Terminate the current task' },
      { id: 'create_chat_completion', name: 'Create Chat Completion', description: 'Create chat completion' },
      { id: 'str_replace_editor', name: 'String Replace Editor', description: 'String replace and edit' },
      { id: 'chart_visualization', name: 'Chart Visualization', description: 'Data chart visualization' },
      { id: 'tool_collection', name: 'Tool Collection', description: 'Tool collection management' },
    ] as AgentTool[],
  };
};

interface AgentToolsState {
  allTools: AgentTool[];
  isLoading: boolean;
  isInitialized: boolean;
  setAllTools: (tools: AgentTool[]) => void;
  setLoading: (loading: boolean) => void;
  setInitialized: (value: boolean) => void;
  refreshTools: () => Promise<void>;
}

const useAgentToolsStore = create<AgentToolsState>((set, get) => ({
  allTools: [],
  isLoading: false,
  isInitialized: false,
  setAllTools: tools => set({ allTools: tools }),
  setLoading: loading => set({ isLoading: loading }),
  setInitialized: value => set({ isInitialized: value }),
  refreshTools: async () => {
    const { setLoading, setAllTools, setInitialized } = get();
    try {
      setLoading(true);
      const response = await listAgentTools();
      if (response.data) {
        setAllTools(response.data);
        setInitialized(true);
      }
    } catch (error) {
      console.error('Failed to fetch tools:', error);
    } finally {
      setLoading(false);
    }
  },
}));

const useAgentTools = () => {
  const { allTools, isLoading, isInitialized, refreshTools } = useAgentToolsStore();

  useEffect(() => {
    if (!isInitialized) {
      refreshTools();
    }
  }, [isInitialized, refreshTools]);

  const getToolByPrefix = useCallback(
    (key: string) => {
      const k = allTools.find(tool => key.startsWith(tool.id));
      if (!k) {
        return {
          toolName: key,
          functionName: '',
        };
      }
      return {
        toolName: k.name,
        functionName: key.includes(`${k.id}-`) ? key.replace(`${k.id}-` || '', '') : '',
      };
    },
    [allTools],
  );

  return {
    allTools,
    isLoading,
    refreshTools,
    getToolByPrefix,
  };
};

export default useAgentTools;
