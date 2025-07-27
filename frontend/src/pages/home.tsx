import { Image } from '@/components/ui/image';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, AlertCircle, Loader2 } from 'lucide-react';
import { createSession } from '@/services/manus';

export default function HomePage() {
  const [inputValue, setInputValue] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const navigate = useNavigate();

  // Handle message sending - create task and navigate
  const handleSubmit = async () => {
    const content = inputValue.trim();
    if (!content || isCreating) return;

    try {
      setIsCreating(true);
      setError(null);

      // Create new chat session
      const response = await createSession({
        prompt: content,
        max_steps: 20,
      });

      if (response.error) {
        setError('Failed to create task, please try again');
        return;
      }

      // Navigate to task details page after successful creation
      navigate(`/tasks/${response.session_id}`);
    } catch (error) {
      console.error('Failed to create task:', error);
      setError('Failed to create task, please try again');
    } finally {
      setIsCreating(false);
    }
  };

  // Handle keyboard events
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (canSend()) {
        handleSubmit();
      }
    }
  };

  // Check if message can be sent
  const canSend = () => {
    return inputValue.trim().length > 0 && !isCreating;
  };

  // Handle error clearing
  const handleClearError = () => {
    setError(null);
  };

  // Get input placeholder text
  const getPlaceholder = () => {
    if (isCreating) return 'Creating task...';
    return 'Enter your question or instruction...';
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
      <div className="pointer-events-none absolute right-0 bottom-0 left-0 p-4">
        <div className="pointer-events-auto mx-auto flex w-full max-w-2xl flex-col gap-2">
          {/* Error message */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>{error}</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleClearError}>
                    Dismiss
                  </Button>
                  <Button size="sm" variant="outline" onClick={handleSubmit} disabled={!inputValue.trim()}>
                    Retry
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}

          {/* Input box */}
          <div className="bg-background dark:bg-background flex w-full flex-col rounded-2xl shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:border">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isCreating}
              placeholder={getPlaceholder()}
              className="min-h-[80px] flex-1 resize-none border-none bg-transparent px-4 py-3 shadow-none outline-none focus-visible:ring-0 focus-visible:ring-offset-0 dark:bg-transparent"
            />
            <div className="border-border flex items-center justify-between border-t px-4 py-2">
              {/* Status indicator */}
              <div className="flex items-center gap-2 text-xs text-gray-500"></div>

              {/* Send button */}
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 cursor-pointer rounded-xl"
                  onClick={handleSubmit}
                  disabled={!canSend()}
                  aria-label="Create task"
                >
                  {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className={`h-4 w-4 ${canSend() ? '' : 'text-gray-400'}`} />}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
