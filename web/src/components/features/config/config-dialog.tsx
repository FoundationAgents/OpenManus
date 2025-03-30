'use client';

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { create } from 'zustand';
import { useForm } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useEffect, useState } from 'react';
import { getLlmConfig, updateLlmConfig } from '@/actions/config';
import { toast } from 'sonner';
import { Form, FormField } from '@/components/ui/form';
import { Slider } from '@/components/ui/slider';
import Link from 'next/link';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import ConfigLlm from './config-llm';
import { Sidebar, SidebarContent, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider } from '@/components/ui/sidebar';
import { cn } from '@/lib/utils';
import ConfigPreferences from './config-preferences';

interface ConfigFormData {
  model: string;
  apiKey: string;
  baseUrl: string;
  maxTokens: number;
  temperature: number;
  apiType: string;
}

export const useConfigDialog = create<{ open: boolean; show: () => void; hide: () => void }>(set => ({
  open: false,
  show: () => set({ open: true }),
  hide: () => set({ open: false }),
}));

export default function ConfigDialog() {
  const { open, show, hide } = useConfigDialog();

  const [currentTab, setCurrentTab] = useState<'llm' | 'preferences'>('llm');

  const form = useForm<ConfigFormData>({
    defaultValues: {
      model: 'gpt-4',
      apiKey: '',
      baseUrl: 'https://api.openai.com/v1',
      maxTokens: 2000,
      temperature: 0.7,
      apiType: 'openai',
    },
    resolver: async data => {
      const errors: any = {};

      if (!data.model) {
        errors.model = {
          type: 'required',
          message: 'Model is required',
        };
      }

      if (!data.apiKey) {
        errors.apiKey = {
          type: 'required',
          message: 'API Key is required',
        };
      }

      if (!data.baseUrl) {
        errors.baseUrl = {
          type: 'required',
          message: 'Base URL is required',
        };
      }

      return {
        values: data,
        errors,
      };
    },
  });

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await getLlmConfig({});
        if (config) {
          form.reset({
            model: config.data?.model || 'deepseek-chat',
            apiKey: config.data?.apiKey || '',
            baseUrl: config.data?.baseUrl || 'https://api.deepseek.com/v1',
            maxTokens: config.data?.maxTokens || 8192,
            temperature: config.data?.temperature || 0.5,
            apiType: '',
          });
        }
      } catch (error) {
        toast.error('Failed to load configuration');
      }
    };
    if (open) {
      loadConfig();
    }
  }, [open, form]);

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
