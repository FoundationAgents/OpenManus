'use client';

import { Label } from '@/components/ui/label';
import { useForm } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useCallback, useEffect, useState } from 'react';
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
import { DialogDescription } from '@/components/ui/dialog';
import { DialogTitle } from '@/components/ui/dialog';
import { DialogHeader } from '@/components/ui/dialog';
import { create } from 'zustand';

interface ConfigFormData {
  model: string;
  apiKey: string;
  baseUrl: string;
  maxTokens: number;
  temperature: number;
  apiType: string;
}

const useLlmConfigStore = create<{ config: ConfigFormData | null; setConfig: (config: ConfigFormData) => void }>(set => ({
  config: null,
  setConfig: (config: ConfigFormData) => set({ config }),
}));

export const useLlmConfig = () => {
  const [loading, setLoading] = useState(true);
  const { config, setConfig } = useLlmConfigStore();

  const refreshConfig = useCallback(async () => {
    setLoading(true);
    const c = await getLlmConfig({});
    if (c && c.data) {
      setConfig(c.data);
    }
    setLoading(false);
  }, [setConfig]);

  useEffect(() => {
    const loadConfig = async () => {
      await refreshConfig();
    };
    loadConfig();
  }, []);

  return { config, loading, refreshConfig };
};

export default function ConfigLlm(props: { onSuccess?: (success: boolean) => void }) {
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingData, setPendingData] = useState<ConfigFormData | null>(null);

  const { config, refreshConfig } = useLlmConfig();

  const form = useForm<ConfigFormData>({
    defaultValues: {
      model: 'deepseek-chat',
      apiKey: '',
      baseUrl: 'https://api.deepseek.com/v1',
      maxTokens: 8192,
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
        if (config) {
          form.reset({
            model: config.model || 'deepseek-chat',
            apiKey: config.apiKey || '',
            baseUrl: config.baseUrl || 'https://api.deepseek.com/v1',
            maxTokens: config.maxTokens || 8192,
            temperature: config.temperature || 0.5,
            apiType: '',
          });
        }
      } catch (error) {
        toast.error('Failed to load configuration');
      }
    };
    loadConfig();
  }, [form]);

  const onSubmit = async (data: ConfigFormData) => {
    setPendingData(data);
    setShowConfirm(true);
  };

  const handleConfirmedSubmit = async () => {
    if (!pendingData) return;

    try {
      setLoading(true);
      await updateLlmConfig(pendingData);
      toast.success('Configuration updated');
      setShowConfirm(false);
      props.onSuccess?.(true);
    } catch (error) {
      toast.error('Failed to update configuration');
      props.onSuccess?.(false);
    } finally {
      setLoading(false);
      await refreshConfig();
    }
  };

  return (
    <>
      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm Configuration</AlertDialogTitle>
            <AlertDialogDescription>Are you sure you want to save these changes? This will update your LLM configuration.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmedSubmit} disabled={loading}>
              {loading ? 'Saving...' : 'Confirm'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <DialogHeader className="mb-2">
        <DialogTitle>LLM Configuration</DialogTitle>
        <DialogDescription>Configure your LLM API settings</DialogDescription>
      </DialogHeader>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="model"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="model" className="flex items-center gap-1">
                  Model
                  <span className="text-red-500">*</span>
                </Label>
                <Input id="model" {...field} placeholder="e.g. deepseek-chat" />
                {form.formState.errors.model && <p className="text-sm text-red-500">{form.formState.errors.model.message}</p>}
              </div>
            )}
          />
          <FormField
            control={form.control}
            name="apiKey"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="apiKey" className="flex items-center gap-1">
                  API Key
                  <span className="text-red-500">*</span>
                </Label>
                <Input id="apiKey" {...field} placeholder="Enter your API Key" />
                {form.formState.errors.apiKey && <p className="text-sm text-red-500">{form.formState.errors.apiKey.message}</p>}
              </div>
            )}
          />
          <FormField
            control={form.control}
            name="baseUrl"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="baseUrl" className="flex items-center gap-1">
                  API Base URL
                  <span className="text-red-500">*</span>
                </Label>
                <Input id="baseUrl" {...field} placeholder="API Base URL" />
                {form.formState.errors.baseUrl && <p className="text-sm text-red-500">{form.formState.errors.baseUrl.message}</p>}
              </div>
            )}
          />
          <FormField
            control={form.control}
            name="maxTokens"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="maxTokens">Max Tokens</Label>
                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <Slider min={1} max={8192} step={1} value={[field.value]} onValueChange={([value]) => field.onChange(value)} />
                  </div>
                  <div className="w-20">
                    <Input
                      type="number"
                      value={field.value}
                      onChange={e => {
                        const value = parseInt(e.target.value);
                        if (!isNaN(value) && value >= 1 && value <= 32000) {
                          field.onChange(value);
                        }
                      }}
                      min={1}
                      max={32000}
                    />
                  </div>
                </div>
              </div>
            )}
          />
          <FormField
            control={form.control}
            name="temperature"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="temperature">Temperature</Label>
                <div className="flex items-center space-x-4">
                  <div className="flex-1">
                    <Slider min={0} max={2} step={0.1} value={[field.value]} onValueChange={([value]) => field.onChange(value)} />
                  </div>
                  <div className="w-20">
                    <Input
                      type="number"
                      value={field.value}
                      onChange={e => {
                        const value = parseFloat(e.target.value);
                        if (!isNaN(value) && value >= 0 && value <= 2) {
                          field.onChange(value);
                        }
                      }}
                      step={0.1}
                      min={0}
                      max={2}
                    />
                  </div>
                </div>
              </div>
            )}
          />
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Link href="https://platform.deepseek.com/" target="_blank" rel="noopener noreferrer" className="text-primary text-sm hover:underline">
                Get API Key from DeepSeek
              </Link>
              <div className="flex space-x-2">
                <Button type="submit" disabled={loading}>
                  {loading ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
            <p className="text-muted-foreground text-center text-xs">
              Your key will be encrypted and stored using{' '}
              <Link
                href="https://pycryptodome.readthedocs.io/en/latest/src/cipher/oaep.html"
                target="_blank"
                className="text-primary hover:underline"
                rel="noopener noreferrer"
              >
                PKCS1_OAEP
              </Link>{' '}
              encryption technology
            </p>
          </div>
        </form>
      </Form>
    </>
  );
}
