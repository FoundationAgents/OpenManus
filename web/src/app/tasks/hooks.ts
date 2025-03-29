import { create } from 'zustand';

const useCurrentMessageIndexStore = create<{
  currentMessageIndex: number;
  setCurrentMessageIndex: (messageIndex: number) => void;
}>(set => ({
  currentMessageIndex: 0,
  setCurrentMessageIndex: messageIndex => set({ currentMessageIndex: messageIndex }),
}));

export const useCurrentMessageIndex = () => {
  const currentMessageIndex = useCurrentMessageIndexStore(state => state.currentMessageIndex);
  const setCurrentMessageIndex = useCurrentMessageIndexStore(state => state.setCurrentMessageIndex);
  return { currentMessageIndex, setCurrentMessageIndex };
};
