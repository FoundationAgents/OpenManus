import React, { useState, useEffect } from 'react';
import LogView from './LogView'; // Reuse LogView for displaying historical logs

const HistoryView = () => {
  const [executions, setExecutions] = useState([]);
  const [selectedExecutionId, setSelectedExecutionId] = useState(null);
  const [historicalLogs, setHistoricalLogs] = useState([]);
  const [isLoadingExecutions, setIsLoadingExecutions] = useState(false);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchExecutions = async () => {
      setIsLoadingExecutions(true);
      setError(null);
      try {
        const response = await fetch('/api/logs/executions');
        if (!response.ok) {
          throw new Error(`Failed to fetch executions: ${response.statusText}`);
        }
        const data = await response.json();
        setExecutions(data);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setIsLoadingExecutions(false);
      }
    };
    fetchExecutions();
  }, []);

  useEffect(() => {
    if (!selectedExecutionId) {
      setHistoricalLogs([]);
      return;
    }
    const fetchLogsForExecution = async () => {
      setIsLoadingLogs(true);
      setError(null);
      try {
        const response = await fetch(`/api/logs/history?execution_id=${selectedExecutionId}&limit=1000`); // Fetch more logs for history
        if (!response.ok) {
          throw new Error(`Failed to fetch logs for ${selectedExecutionId}: ${response.statusText}`);
        }
        const data = await response.json();
        setHistoricalLogs(data);
      } catch (err) {
        console.error(err);
        setError(err.message);
      } finally {
        setIsLoadingLogs(false);
      }
    };
    fetchLogsForExecution();
  }, [selectedExecutionId]);

  if (selectedExecutionId) {
    return (
      <div className="p-4 flex-grow flex flex-col bg-gray-800 text-white">
        <button
          onClick={() => setSelectedExecutionId(null)}
          className="mb-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-max"
        >
          &larr; Back to Executions List
        </button>
        <h2 className="text-xl font-semibold mb-2">Logs for Execution: {selectedExecutionId}</h2>
        {isLoadingLogs && <p>Loading logs...</p>}
        {error && <p className="text-red-400">Error: {error}</p>}
        <div className="flex-grow overflow-hidden"> {/* Ensure LogView itself can scroll */}
          <LogView logs={historicalLogs} />
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 flex-grow bg-gray-800 text-white overflow-y-auto">
      <h2 className="text-2xl font-semibold mb-4 text-gray-100">Execution History</h2>
      {isLoadingExecutions && <p>Loading execution list...</p>}
      {error && <p className="text-red-400">Error: {error}</p>}
      {executions.length === 0 && !isLoadingExecutions && <p>No execution history found.</p>}
      <ul className="space-y-2">
        {executions.map((exec) => (
          <li key={exec.execution_id}>
            <button
              onClick={() => setSelectedExecutionId(exec.execution_id)}
              className="w-full text-left p-3 bg-gray-700 hover:bg-gray-600 rounded shadow"
            >
              <span className="font-semibold text-blue-400">{exec.execution_id}</span>
              <span className="block text-xs text-gray-400">Started: {new Date(exec.start_time).toLocaleString()}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default HistoryView;
