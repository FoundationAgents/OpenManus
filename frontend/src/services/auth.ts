export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

export async function getMe(): Promise<{ user?: User }> {
  const response = await fetch('/api/auth/me', { credentials: 'same-origin' });
  if (!response.ok) return {};
  return response.json();
}

export async function login(email: string, password: string): Promise<{ user?: User; error?: string }> {
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Could not sign in');
    return { user: data.user };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Could not sign in' };
  }
}

export async function signup(name: string, email: string, password: string): Promise<{ user?: User; error?: string }> {
  try {
    const response = await fetch('/api/auth/signup', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Could not create account');
    return { user: data.user };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Could not create account' };
  }
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
  });
}
