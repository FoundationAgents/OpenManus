import React from 'react';

const ToolsView = ({ tools }) => {
  if (!tools || tools.length === 0) {
    return <div className="p-4 text-gray-300">No tools available or loaded.</div>;
  }

  return (
    <div className="p-4 flex-grow overflow-y-auto bg-gray-800 text-white">
      <h2 className="text-2xl font-semibold mb-4 text-gray-100">Available Tools</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {(tools || []).map((tool, index) => (
          <div key={index} className="bg-gray-700 p-4 rounded-lg shadow">
            <h3 className="text-xl font-bold text-blue-400 mb-2">{tool.name}</h3>
            <p className="text-sm text-gray-300 mb-1">{tool.description || "No description available."}</p>
            <h4 className="text-md font-semibold mt-2 mb-1 text-gray-200">Parameters:</h4>
            {tool.parameters && typeof tool.parameters === 'object' && Object.keys(tool.parameters).length > 0 ? (
              <pre className="text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                {JSON.stringify(tool.parameters, null, 2)}
              </pre>
            ) : (
              <p className="text-xs text-gray-400 italic">No parameters specified or parameters format not recognized.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ToolsView;
