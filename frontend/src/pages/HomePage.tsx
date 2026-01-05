import { createTask } from '@/services/tasks';
import { ChatInput } from '@/components/features/chat/input';
import { Image } from '@/components/ui/image';
import { useRecentTasks } from '@/hooks/use-tasks';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function HomePage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const { refreshTasks } = useRecentTasks();

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSubmit = async (input: { prompt: string }) => {
    if (!input || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setIsLoading(true);

    try {
      const res = await createTask({ prompt: input.prompt });
      if (res.error || !res.data) {
        throw new Error('Failed to create task');
      }
      await refreshTasks();
      navigate(`/tasks/${res.data.task_id}`);
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return;
      }
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4 pb-20">
        <div className="flex h-full flex-col items-center justify-center opacity-50">
          <Image src="/logo.jpg" alt="OpenManus" className="mb-4 object-contain" width={200} height={200} />
          <div>No fortress, purely open ground. OpenManus is Coming.</div>
        </div>
      </div>
      <ChatInput onSubmit={handleSubmit} status={isLoading ? 'thinking' : 'idle'} />
    </div>
  );
}
