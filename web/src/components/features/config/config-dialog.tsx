'use client';

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { create } from 'zustand';

export const useConfigDialog = create<{ open: boolean; show: () => void; hide: () => void }>(set => ({
  open: false,
  show: () => set({ open: true }),
  hide: () => set({ open: false }),
}));

export default function ConfigDialog() {
  const { open, show, hide } = useConfigDialog();
  return (
    <Dialog open={open} onOpenChange={open => (open ? show() : hide())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Config</DialogTitle>
        </DialogHeader>
        <DialogDescription>Configure your account and preferences.</DialogDescription>
      </DialogContent>
    </Dialog>
  );
}
