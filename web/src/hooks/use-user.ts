import { getMe } from '@/actions/me';
import { create } from 'zustand';

const useMeStore = create<{ me: Awaited<ReturnType<typeof getMe>>['data'] | null; refreshMe: () => Promise<void> }>(set => ({
  me: null,
  refreshMe: async () => {
    const res = await getMe({});
    set({ me: res.data });
  },
}));

const useMe = () => {
  const { me, refreshMe } = useMeStore();
  return { me, refreshMe };
};

export default useMe;
