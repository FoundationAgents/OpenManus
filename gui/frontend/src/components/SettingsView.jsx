import React from 'react';

const SettingsView = ({ config }) => {
  if (!config || Object.keys(config).length === 0) {
    return <div className="p-4 text-gray-300">No configuration loaded.</div>;
  }

  const renderConfigValue = (value) => {
    if (typeof value === 'boolean') {
      return value ? 'Enabled' : 'Disabled';
    }
    if (typeof value === 'object' && value !== null) {
      return <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto">{JSON.stringify(value, null, 2)}</pre>;
    }
    return String(value);
  };

  return (
    <div className="p-4 flex-grow overflow-y-auto bg-gray-800 text-white">
      <h2 className="text-2xl font-semibold mb-4 text-gray-100">Agent Configuration</h2>
      <div className="bg-gray-700 p-4 rounded-lg shadow">
        {Object.entries(config).map(([key, value]) => (
          <div key={key} className="mb-3 pb-3 border-b border-gray-600 last:border-b-0">
            <h3 className="text-lg font-medium text-blue-400 capitalize">{key.replace(/_/g, ' ')}:</h3>
            <div className="text-sm text-gray-300 mt-1">
              {renderConfigValue(value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SettingsView;
