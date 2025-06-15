import React, { useState, useEffect, useRef } from 'react';

// Removed sampleLogs

const LogView = ({ logs }) => { // logs prop is now the primary source
  // Removed: const [logEntries, setLogEntries] = useState(logs || sampleLogs);
  // Removed: useEffect(() => { setLogEntries(logs || sampleLogs); }, [logs]);
  
  // Keep:
  const [filterLevel, setFilterLevel] = useState('ALL');
  const logEndRef = useRef(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]); // Scroll when new logs arrive via props

  const getLevelColor = (level) => {
    if (!level) return 'text-gray-700'; // Handle undefined level
    switch (level.toUpperCase()) { // Ensure level is not undefined before calling toUpperCase
      case 'ERROR': return 'text-red-500';
      case 'WARN': return 'text-yellow-500';
      case 'USER_INPUT': return 'text-purple-400'; // Added for user input styling
      case 'INFO': return 'text-blue-500';
      case 'DEBUG': return 'text-gray-500';
      case 'STDOUT': return 'text-green-500'; // For subprocess stdout
      case 'STDERR': return 'text-red-700';   // For subprocess stderr
      default: return 'text-gray-700';
    }
  };

  const filteredLogs = (logs || []).filter(log => // Ensure logs is not undefined
    filterLevel === 'ALL' || (log.level && log.level.toUpperCase() === filterLevel)
  );
  
  return (
    // Ensure LogView itself is set to take available space and scroll internally
    // The parent div in App.jsx has overflow-hidden, so LogView needs to manage its own scroll.
    <div className="flex-grow flex flex-col bg-gray-800 text-white p-4 overflow-y-auto"> {/* Removed fixed height, rely on flex-grow and parent's overflow-hidden */}
      <div className="mb-4 shrink-0"> {/* Added shrink-0 to prevent filter bar from shrinking */}
        <label htmlFor="logLevelFilter" className="mr-2 text-gray-300">Filter by level:</label>
        <select 
          id="logLevelFilter" 
          value={filterLevel} 
          onChange={(e) => setFilterLevel(e.target.value)}
          className="bg-gray-700 text-white p-1 rounded"
        >
          <option value="ALL">ALL</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARN">WARN</option>
          <option value="ERROR">ERROR</option>
          <option value="STDOUT">STDOUT</option>
          <option value="STDERR">STDERR</option>
          <option value="USER_INPUT">USER_INPUT</option> {/* Added USER_INPUT to filter */}
        </select>
      </div>
      {/* This div will handle the scrolling of logs */}
      <div className="flex-grow overflow-y-auto"> 
        {filteredLogs.map((log, index) => (
          <div key={log.id || index} className={`font-mono text-sm mb-1 p-1 rounded ${(log.level && log.level.toUpperCase() === 'ERROR') ? 'bg-red-900/30' : (log.level && log.level.toUpperCase() === 'WARN') ? 'bg-yellow-900/30' : ''}`}>
            <span className="mr-2 text-gray-400">{log.time && log.time.repr}</span> {/* Check log.time exists */}
            <span className={`font-bold mr-2 ${getLevelColor(log.level)}`}>[{log.level ? log.level.toUpperCase() : 'N/A'}]</span> {/* Check log.level exists */}
            <span className="text-purple-400 mr-2">[{log.name}:{log.function}:{log.line}]</span>
            <span className="whitespace-pre-wrap">{log.text}</span> {/* Ensure log.text is string */}
          </div>
        ))}
        <div ref={logEndRef} /> {/* This div is used to scroll to the bottom */}
      </div>
    </div>
  );
};

export default LogView;
