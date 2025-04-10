import { installTool } from '@/actions/tools';
import { Button } from '@/components/ui/button';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import * as z from 'zod';

interface ToolConfigFormProps {
  tool: {
    id: string;
    name: string;
    envSchema: any;
  };
  onSuccess?: () => void;
}

export const ToolConfigForm = ({ tool, onSuccess }: ToolConfigFormProps) => {
  const [isLoading, setIsLoading] = useState(false);

  const generateZodSchema = (schema: any) => {
    const zodSchema: Record<string, any> = {};

    if (schema.properties) {
      Object.entries(schema.properties).forEach(([key, value]: [string, any]) => {
        let zodType;
        switch (value.type) {
          case 'string':
            zodType = z.string();
            break;
          case 'number':
            zodType = z.number();
            break;
          case 'boolean':
            zodType = z.boolean();
            break;
          default:
            zodType = z.string();
        }

        if (value.required) {
          zodSchema[key] = zodType;
        } else {
          zodSchema[key] = zodType.optional();
        }
      });
    }

    return z.object(zodSchema);
  };

  const formSchema = generateZodSchema(tool.envSchema);
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {},
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    try {
      setIsLoading(true);
      await installTool({
        toolId: tool.id,
        env: values,
      });
      toast.success('Install success', {
        description: 'Tool config saved',
      });
      onSuccess?.();
    } catch (error) {
      toast.error('Install failed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        {tool.envSchema.properties &&
          Object.entries(tool.envSchema.properties).map(([key, value]: [string, any]) => (
            <FormField
              key={key}
              control={form.control}
              name={key}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{value.title || key}</FormLabel>
                  <FormControl>
                    <Input type={value.type === 'number' ? 'number' : 'text'} placeholder={value.description} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          ))}
        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? 'Installing...' : 'Install Tool'}
        </Button>
      </form>
    </Form>
  );
};
