import { createConversation, listConversations, type Conversation } from '@/services/conversations';
import { create } from 'zustand';

interface ConversationStore {
  conversations: Conversation[];
  activeConversationId?: string;
  refreshConversations: () => Promise<void>;
  ensureConversation: () => Promise<string | undefined>;
  createNewConversation: () => Promise<Conversation>;
  setActiveConversationId: (conversationId?: string) => void;
  removeConversation: (conversationId: string) => void;
}

const STORAGE_KEY = 'openmanus.activeConversationId';

export const useConversations = create<ConversationStore>((set, get) => ({
  conversations: [],
  activeConversationId: localStorage.getItem(STORAGE_KEY) || undefined,
  refreshConversations: async () => {
    const res = await listConversations();
    const conversations = res.conversations || [];
    const current = get().activeConversationId;
    const activeConversationId =
      current && conversations.some(item => item.id === current)
        ? current
        : conversations[0]?.id;
    if (activeConversationId) localStorage.setItem(STORAGE_KEY, activeConversationId);
    set({ conversations, activeConversationId });
  },
  ensureConversation: async () => {
    if (!get().conversations.length) {
      await get().refreshConversations();
    }
    if (get().activeConversationId) return get().activeConversationId;
    const conversation = await get().createNewConversation();
    return conversation.id;
  },
  createNewConversation: async () => {
    const conversation = await createConversation();
    localStorage.setItem(STORAGE_KEY, conversation.id);
    set(state => ({
      conversations: [conversation, ...state.conversations],
      activeConversationId: conversation.id,
    }));
    return conversation;
  },
  setActiveConversationId: conversationId => {
    if (conversationId) {
      localStorage.setItem(STORAGE_KEY, conversationId);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    set({ activeConversationId: conversationId });
  },
  removeConversation: conversationId => {
    set(state => {
      const conversations = state.conversations.filter(item => item.id !== conversationId);
      const activeConversationId =
        state.activeConversationId === conversationId ? conversations[0]?.id : state.activeConversationId;
      if (activeConversationId) localStorage.setItem(STORAGE_KEY, activeConversationId);
      else localStorage.removeItem(STORAGE_KEY);
      return { conversations, activeConversationId };
    });
  },
}));
