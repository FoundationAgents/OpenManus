import React, { useState } from 'react';

const UserInput = ({ onSendMessage, disabled, placeholderText }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && onSendMessage) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-gray-200 shrink-0"> {/* Added shrink-0 */}
      <div className="flex items-center">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={placeholderText || "Enter your prompt or feedback..."}
          className="flex-grow p-2 border border-gray-400 rounded-l-md focus:ring-blue-500 focus:border-blue-500"
          disabled={disabled}
        />
        <button
          type="submit"
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-r-md disabled:opacity-50"
          disabled={disabled}
        >
          Send
        </button>
      </div>
    </form>
  );
};

export default UserInput;
