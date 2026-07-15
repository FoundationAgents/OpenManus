import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { login, signup, type User } from '@/services/auth';
import { Lock, LogIn, UserPlus } from 'lucide-react';
import { useState, type FormEvent } from 'react';

interface AuthPageProps {
  onSignedIn: (user: User) => void;
}

export default function AuthPage({ onSignedIn }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');
    const result =
      mode === 'login'
        ? await login(email, password)
        : await signup(name || email.split('@')[0], email, password);
    setIsLoading(false);
    if (result.error || !result.user) {
      setError(result.error || 'Could not continue');
      return;
    }
    onSignedIn(result.user);
  };

  return (
    <main className="flex h-screen w-screen items-center justify-center bg-background p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <div className="space-y-2">
          <div className="flex size-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Lock className="size-5" />
          </div>
          <h1 className="text-2xl font-semibold tracking-normal">OpenManus</h1>
          <p className="text-sm text-muted-foreground">
            Sign in to keep conversations, workspaces, and agent runs isolated.
          </p>
        </div>

        <div className="flex rounded-md border p-1">
          <Button
            type="button"
            variant={mode === 'login' ? 'secondary' : 'ghost'}
            className="flex-1"
            onClick={() => setMode('login')}
          >
            <LogIn className="size-4" />
            Sign in
          </Button>
          <Button
            type="button"
            variant={mode === 'signup' ? 'secondary' : 'ghost'}
            className="flex-1"
            onClick={() => setMode('signup')}
          >
            <UserPlus className="size-4" />
            Sign up
          </Button>
        </div>

        {mode === 'signup' && (
          <Input
            autoComplete="name"
            placeholder="Name"
            value={name}
            onChange={event => setName(event.target.value)}
          />
        )}
        <Input
          autoComplete="email"
          type="email"
          placeholder="Email"
          value={email}
          onChange={event => setEmail(event.target.value)}
          required
        />
        <Input
          autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          type="password"
          placeholder="Password"
          value={password}
          onChange={event => setPassword(event.target.value)}
          required
        />
        {error && <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">{error}</div>}
        <Button className="w-full" disabled={isLoading}>
          {isLoading ? 'Working...' : mode === 'login' ? 'Sign in' : 'Create account'}
        </Button>
      </form>
    </main>
  );
}
