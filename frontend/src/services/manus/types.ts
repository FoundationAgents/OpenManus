// Manus business-related type definitions

// Re-export types from chat-messages to maintain compatibility
export type {
  ManusMessage,
  StreamStatus as SessionStatusType
} from '@/libs/chat-messages';

// ==================== Session management related ====================

export interface CreateSessionRequest {
  prompt: string;
  max_steps?: number;
  max_observe?: number;
  session_id?: string;
}

export interface CreateSessionResponse {
  session_id: string;
  status: string;
  result?: any;
  error?: string;
}

export interface SessionStatus {
  session_id: string;
  status: 'idle' | 'connecting' | 'connected' | 'processing' | 'completed' | 'error';
  progress?: number;
  current_step?: number;
}

// ==================== Complete session state ====================

export interface ChatSession {
  id: string;
  messages: any[]; // Use Message type from chat-messages library
  status: SessionStatus['status'];
  error?: string;
}
