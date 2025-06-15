import React, { useState, useEffect, useCallback } from 'react';
import LogView from './components/LogView';
import UserInput from './components/UserInput';
import PlanDisplay from './components/PlanDisplay';
import ToolsView from './components/ToolsView';
import HistoryView from './components/HistoryView'; // Import HistoryView
import SettingsView from './components/SettingsView'; // Import SettingsView

// Assuming a Sidebar component will be created later or is part of this step if simple enough
// For now, keep the inline sidebar structure.

function App() {
  const [logs, setLogs] = useState([]);
  const [agentStatus, setAgentStatus] = useState({ is_running: false, is_waiting_for_input: false, execution_id: null });
  const [tools, setTools] = useState([]);
  const [agentConfig, setAgentConfig] = useState({});
  const [currentExecutionId, setCurrentExecutionId] = useState(null);
  const [agentPlan, setAgentPlan] = useState(null); // New state for agent plan
  const [mainView, setMainView] = useState('logs'); // 'logs', 'tools', 'history', 'settings'


  // Fetch initial data (status, tools, config)
  useEffect(() => {
    const fetchData = async () => {
      try {
        const statusRes = await fetch('/api/agent/status');
        setAgentStatus(await statusRes.json());

        const toolsRes = await fetch('/api/agent/tools');
        setTools(await toolsRes.json());

        const configRes = await fetch('/api/agent/config');
        setAgentConfig(await configRes.json());
      } catch (error) {
        console.error("Error fetching initial data:", error);
        // Add user-friendly error log to the log view
        setLogs(prev => [...prev, {
          id: Date.now(), level: 'ERROR', time: { repr: new Date().toISOString() },
          name: 'GUI', function: 'fetchInitialData', line: 1,
          text: `Failed to fetch initial data: ${error.message}`
        }]);
      }
    };
    fetchData();
  }, []);

  // SSE Connection for Logs
  useEffect(() => {
    const eventSource = new EventSource('/api/logs/stream');
    eventSource.onmessage = function(event) {
      const logEntry = JSON.parse(event.data);
      setLogs(prevLogs => [...prevLogs, logEntry]);
    };
    eventSource.onerror = function(err) {
      console.error("EventSource failed:", err);
      setLogs(prev => [...prev, {
        id: Date.now(), level: 'ERROR', time: { repr: new Date().toISOString() },
        name: 'GUI', function: 'SSE', line: 1,
        text: 'Log stream connection error. Refresh or check backend.'
      }]);
      eventSource.close();
    };

    // Cleanup on component unmount
    return () => {
      eventSource.close();
    };
  }, []); // Empty dependency array means this effect runs once on mount and cleans up on unmount

  // Poll for agent status periodically if you want to update UI based on it,
  // e.g., when agent becomes busy or awaits input without direct SSE signal for status change.
  useEffect(() => {
    const intervalId = setInterval(async () => {
      try {
        const statusRes = await fetch('/api/agent/status');
        const newStatus = await statusRes.json();
        setAgentStatus(newStatus);
        if (newStatus.execution_id) {
            setCurrentExecutionId(newStatus.execution_id);
        }

        // Fetch plan if agent is running and has an execution_id
        if (newStatus.execution_id && newStatus.is_running) {
          try {
            const planRes = await fetch('/api/agent/plan');
            if (planRes.ok) {
              const planData = await planRes.json();
              // Check if planData is not null and has steps, or if it's an error message from backend
              if (planData && (planData.steps || planData.error)) {
                setAgentPlan(planData);
              } else if (planData && Object.keys(planData).length === 0) { // Empty object means no plan
                setAgentPlan(null);
              } else if (!planData) { // Explicitly null/undefined from backend
                setAgentPlan(null);
              }
              // If planData is an empty object from a successful fetch, treat as no plan
              // This handles cases where backend returns {} for no plan vs. error or actual plan.
            } else {
              setAgentPlan(null); // Reset plan on non-OK response (e.g., 404)
            }
          } catch (error) {
            console.error("Error fetching agent plan:", error);
            setAgentPlan(null);
          }
        } else if (!newStatus.is_running) {
            setAgentPlan(null); // Clear plan if agent is not running
        }

      } catch (error) {
        console.error("Error fetching agent status:", error);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(intervalId);
  }, []); // Removed agentStatus.execution_id from deps to avoid re-triggering interval setup


  const handleSendMessage = useCallback(async (message) => {
    const userMessageLog = {
      id: `user-${Date.now()}`, level: 'USER_INPUT', time: { repr: new Date().toISOString() },
      name: 'User', function: 'input', line: 1, text: message
    };
    setLogs(prevLogs => [...prevLogs, userMessageLog]);

    try {
      if (agentStatus.is_waiting_for_input && currentExecutionId) {
        // Agent is waiting for input for the current execution
        const response = await fetch('/api/agent/input', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_input: message, execution_id: currentExecutionId }) // Include execution_id if your backend needs it here
        });
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);
        // Status will update via polling or SSE log indicating input was processed
      } else {
        // Start a new agent session
        if (agentStatus.is_running) {
             setLogs(prev => [...prev, {
                id: Date.now(), level: 'WARN', time: { repr: new Date().toISOString() },
                name: 'GUI', function: 'handleSendMessage', line: 1,
                text: `An agent is already running (ID: ${currentExecutionId}). Please wait or implement multiple agent support.`
            }]);
            return;
        }
        const response = await fetch('/api/agent/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: message, agent_type: "manus" }) // agent_type can be dynamic
        });
        if (!response.ok) throw new Error(`API error: ${response.statusText}`);
        const data = await response.json();
        setCurrentExecutionId(data.execution_id);
        // Agent status will be updated via polling or logs
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setLogs(prev => [...prev, {
        id: Date.now(), level: 'ERROR', time: { repr: new Date().toISOString() },
        name: 'GUI', function: 'handleSendMessage', line: 1,
        text: `Failed to send message: ${error.message}`
      }]);
    }
  }, [agentStatus, currentExecutionId]); // Dependencies for useCallback

  return (
    <div className="flex h-screen antialiased text-gray-800">
      {/* Sidebar Placeholder */}
      <div className="w-64 bg-gray-900 text-white p-4 flex flex-col shrink-0">
        <h2 className="text-xl font-semibold mb-4">OpenMAN</h2>
        <nav className="flex-grow">
          <ul>
            <li className="mb-2">
              <a href="#" onClick={(e) => { e.preventDefault(); setMainView('logs'); }} 
                 className={`block py-1 px-2 rounded hover:bg-gray-700 text-sm ${mainView === 'logs' ? 'text-blue-400 font-semibold bg-gray-700' : 'hover:text-gray-300'}`}>
                Dashboard/Logs
              </a>
            </li>
            <li className="mb-2">
              <a href="#" onClick={(e) => { e.preventDefault(); setMainView('tools'); }} 
                 className={`block py-1 px-2 rounded hover:bg-gray-700 text-sm ${mainView === 'tools' ? 'text-blue-400 font-semibold bg-gray-700' : 'hover:text-gray-300'}`}>
                Tools ({tools.length})
              </a>
            </li>
             <li className="mb-2">
                <span className={`block py-1 px-2 text-sm ${agentStatus.is_running ? (agentStatus.agent_state === 'WaitingForHumanInput' || agentStatus.is_waiting_for_input ? 'text-yellow-400' : 'text-green-400') : 'text-gray-400'}`}>
                 Status: {agentStatus.agent_state || (agentStatus.is_running ? (agentStatus.is_waiting_for_input ? 'Waiting For Input' : 'Running') : 'Idle')}
                </span>
            </li>
            <li className="mb-2">
                <a href="#" onClick={(e) => { e.preventDefault(); setMainView('history'); }} 
                   className={`block py-1 px-2 rounded hover:bg-gray-700 text-sm ${mainView === 'history' ? 'text-blue-400 font-semibold bg-gray-700' : 'hover:text-gray-300'}`}>
                   History
                </a>
            </li>
            <li className="mb-2">
                <a href="#" onClick={(e) => { e.preventDefault(); setMainView('settings'); }} 
                   className={`block py-1 px-2 rounded hover:bg-gray-700 text-sm ${mainView === 'settings' ? 'text-blue-400 font-semibold bg-gray-700' : 'hover:text-gray-300'}`}>
                   Settings
                </a>
            </li>
          </ul>
        </nav>
        <div className="mt-auto">
          <p className="text-xs text-gray-500">Version 0.1.0</p>
          <p className="text-xs text-gray-500 truncate" title={currentExecutionId || ""}>Exec ID: {currentExecutionId || 'N/A'}</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-grow flex flex-col overflow-hidden">
        {mainView === 'logs' && (
          <>
            {/* Ensure agentPlan is not null and doesn't have an error before rendering PlanDisplay */}
            {agentPlan && !agentPlan.error && agentPlan.steps && agentPlan.steps.length > 0 && <PlanDisplay plan={agentPlan} />}
            <LogView logs={logs} />
          </>
        )}
        {mainView === 'tools' && <ToolsView tools={tools} />}
        {mainView === 'history' && <HistoryView />}
        {mainView === 'settings' && <SettingsView config={agentConfig} />}
        
        {/* UserInput should only be visible for 'logs' view */}
        {mainView === 'logs' && <UserInput 
          onSendMessage={handleSendMessage} 
          disabled={agentStatus.is_running && !agentStatus.is_waiting_for_input}
          placeholderText={
              agentStatus.is_waiting_for_input 
              ? "Agent is waiting for your input..." 
              : agentStatus.is_running 
              ? "Agent is processing..." 
              : "Enter your prompt to start..."
          }
        />}
      </div>
    </div>
  );
}

export default App;
