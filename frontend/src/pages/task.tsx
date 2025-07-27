import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { ManusMessageSocket, type ManusMessage, type Message } from '@/libs/chat-messages';
import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

const useConversation = (taskId: string | undefined) => {
  const [messages, setMessages] = useState<Message[]>([]);

  const streamRef = useRef<ManusMessageSocket<ManusMessage> | null>(
    new ManusMessageSocket<ManusMessage>({
      url: '',
      onMessage: (message: Message) => {
        setMessages(prevMessages => {
          const updatedMessages = [...prevMessages, message];
          return updatedMessages;
        });
      },
    }),
  );

  // Auto-connect when component mounts
  useEffect(() => {
    if (!taskId) return;
    streamRef.current?.connect(`http://localhost:8000/api/manus/sessions/ws/${taskId}`);
    return () => {
      if (streamRef.current) {
        streamRef.current.disconnect();
        streamRef.current = null;
      }
    };
  }, [taskId]);

  return { messages, stream: streamRef };
};

const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const { messages } = useConversation(taskId);

  return (
    <div className="flex h-full gap-2 p-4">
      {/* Left: Chat Messages */}
      <div className="flex w-full flex-col overflow-auto">
        <ChatMessages messages={messages} />
      </div>

      {/* Right: Terminal Preview */}
      <ChatPreview taskId={taskId || ''} messages={messages} />
    </div>
  );
};

export default TaskDetailPage;
