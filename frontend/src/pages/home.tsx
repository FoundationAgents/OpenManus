import { ChatInput } from '@/components/features/chat/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Image } from '@/components/ui/image';
import { useRecentTasks } from '@/hooks/use-tasks';
import { createSession } from '@/services/manus';
import { AlertCircle } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function HomePage() {
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { addTask, refreshTasks } = useRecentTasks();

  // Handle message sending - create task and navigate
  const handleSubmit = async (value: { taskId?: string; prompt: string }) => {
    if (!value.prompt) return;

    try {
      // Create new chat session
      const response = await createSession({
        prompt: value.prompt,
        max_steps: 20,
      });

      if (response.error) {
        setError('Failed to create task, please try again');
        return;
      }

      // Add task to the task list
      addTask({
        id: response.session_id,
        created_at: new Date().toISOString(),
        request: value.prompt,
        status: 'initializing',
        progress: 0,
      });

      // Navigate to task details page after successful creation
      navigate(`/tasks/${response.session_id}`);

      // Refresh task list to get latest status
      setTimeout(() => {
        refreshTasks();
      }, 1000);
    } catch (error) {
      console.error('Failed to create task:', error);
      setError('Failed to create task, please try again');
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4 pb-32">
        {/* Welcome screen */}
        <div className="flex h-full flex-col items-center justify-center opacity-50">
          <Image src="/logo.jpg" alt="OpenManus" className="mb-4 object-contain" width={160} height={160} />
          <div className="space-y-2 text-center">
            <div className="text-gray-600 dark:text-gray-400">No fortress, purely open ground. OpenManus is Coming.</div>
          </div>
        </div>
      </div>

      {/* Input area */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <ChatInput status="idle" onSubmit={handleSubmit} taskId={undefined} className="p-4" />
    </div>
  );
}
