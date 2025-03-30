'use client';

import logo from '@/assets/logo.png';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send } from 'lucide-react';
import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createTask } from '@/actions/tasks';
import { useRecentTasks } from '@/components/features/app-sidebar';

const EmptyState = () => (
  <div className="flex h-full flex-col items-center justify-center opacity-50">
    <Image src={logo} alt="OpenManus" className="mb-4 object-contain" width={240} height={240} />
    <div>No fortress, purely open ground. OpenManus is Coming.</div>
  </div>
);

export default function ChatPage() {
  const router = useRouter();
  const [input, setInput] = useState('');
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setInput('');
    setIsLoading(true);

    try {
      const res = await createTask({ prompt: input });
      if (res.error || !res.data) {
        throw new Error('Failed to create task');
      }
      await refreshTasks();
      router.push(`/tasks/${res.data.id}`);
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
    <div className="flex h-screen flex-col bg-gray-100">
      <div className="flex-1 space-y-4 overflow-y-auto p-4 pb-20">
        <EmptyState />
      </div>

      <div className="pointer-events-none absolute right-0 bottom-0 left-0 p-4">
        <form onSubmit={handleSubmit} className="pointer-events-auto mx-auto w-full max-w-2xl">
          <div className="relative flex rounded-2xl bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)]">
            <Input
              value={isLoading ? 'Thinking...' : input}
              aria-disabled={isLoading}
              onChange={e => setInput(e.target.value)}
              placeholder="Let's Imagine the Impossible, Create the Future Together"
              className="h-12 flex-1 border-0 bg-transparent px-4 focus-visible:ring-0 focus-visible:ring-offset-0"
              disabled={isLoading}
            />
            <Button
              type="submit"
              disabled={isLoading}
              size="icon"
              variant="ghost"
              className="absolute top-1/2 right-1 h-10 w-10 -translate-y-1/2 cursor-pointer rounded-xl hover:bg-gray-100"
            >
              <Send className="h-5 w-5" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
