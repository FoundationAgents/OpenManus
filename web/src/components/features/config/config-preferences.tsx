'use client';

import { getPreferences, updatePreferences } from '@/actions/config';
import { Button } from '@/components/ui/button';
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormField } from '@/components/ui/form';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LANGUAGE_CODE_OPTIONS } from '@/lib/language';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';

interface ConfigFormData {
  language?: string;
}

export default function ConfigLlm(props: { onSuccess?: (success: boolean) => void }) {
  const [loading, setLoading] = useState(false);

  const form = useForm<ConfigFormData>({
    defaultValues: { language: '' },
  });

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const config = await getPreferences({});
        form.reset({ language: config.data?.language || undefined });
      } catch (error) {
        toast.error('Failed to load configuration');
      }
    };
    loadConfig();
  }, [form]);

  const onSubmit = async (data: ConfigFormData) => {
    setLoading(true);
    await updatePreferences({ language: data.language });
    setLoading(false);
    toast.success('Preferences updated');
    props.onSuccess?.(true);
  };

  return (
    <>
      <DialogHeader className="mb-2">
        <DialogTitle>Preferences</DialogTitle>
        <DialogDescription>Configure your preferences</DialogDescription>
      </DialogHeader>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            control={form.control}
            name="language"
            render={({ field }) => (
              <div className="space-y-2">
                <Label htmlFor="language" className="flex items-center gap-1">
                  Language (LLM Answer)
                </Label>
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a language" />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGE_CODE_OPTIONS.map(language => (
                      <SelectItem key={language.value} value={language.value}>
                        {language.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          />
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </Form>
    </>
  );
}
