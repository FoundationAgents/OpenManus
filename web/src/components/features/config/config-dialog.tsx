'use client';

import { Dialog, DialogContent } from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { create } from 'zustand';
import ConfigLlm from './config-llm';
import ConfigPreferences from './config-preferences';

export const useConfigDialog = create<{ open: boolean; show: () => void; hide: () => void }>(set => ({
  open: false,
  show: () => set({ open: true }),
  hide: () => set({ open: false }),
}));

export default function ConfigDialog() {
  const { open, show, hide } = useConfigDialog();

  const [currentTab, setCurrentTab] = useState<'llm' | 'preferences'>('llm');

  return (
    <Dialog open={open} onOpenChange={open => (open ? show() : hide())}>
      <DialogContent className="w-auto pb-1 pl-1" style={{ maxWidth: '100%' }}>
        <div className="flex min-h-[500px] w-[800px] gap-4 pl-4">
          {/* Sidebar */}
          <div className="flex w-[200px] flex-col gap-2">
            <div
              onClick={() => setCurrentTab('llm')}
              className={cn(
                currentTab === 'llm' && 'text-primary',
                'cursor-pointer',
                'rounded-md p-2',
                'hover:bg-muted',
                'transition-colors',
                currentTab === 'llm' && 'bg-muted',
              )}
            >
              LLM Configuration
            </div>
            <div
              onClick={() => setCurrentTab('preferences')}
              className={cn(
                currentTab === 'preferences' && 'text-primary',
                'cursor-pointer',
                'rounded-md p-2',
                'hover:bg-muted',
                'transition-colors',
                currentTab === 'preferences' && 'bg-muted',
              )}
            >
              Preferences
            </div>
          </div>
          {/* Content */}
          <div className="flex-1">
            {currentTab === 'llm' && <ConfigLlm />}
            {currentTab === 'preferences' && <ConfigPreferences />}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
