// Manus session management - responsible for session lifecycle HTTP API operations

import type { CreateSessionRequest, CreateSessionResponse } from './types';

/**
 * Create a new Manus conversation session
 * @param request Session creation request
 * @returns Session creation response
 */
export async function createSession(
  request: CreateSessionRequest
): Promise<CreateSessionResponse> {
  try {
    const response = await fetch('/api/manus/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to create Manus session:', error);
    throw error;
  }
}

