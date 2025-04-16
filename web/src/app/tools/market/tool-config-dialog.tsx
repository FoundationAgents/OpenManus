import { installTool } from '@/actions/tools';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { zodResolver } from '@hookform/resolvers/zod';
import { Tools } from '@prisma/client';
import { JSONSchema } from 'json-schema-to-ts';
import { forwardRef, useImperativeHandle, useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import * as z from 'zod';

interface ToolInfo {
  id: string;
  name: string;
  envSchema: Exclude<JSONSchema, boolean>;
}

interface ToolConfigDialogProps {
  onSuccess?: () => void;
}

export interface ToolConfigDialogRef {
  showConfig: (tool: Tools) => void;
}

export const ToolConfigDialog = forwardRef<ToolConfigDialogRef, ToolConfigDialogProps>(({ onSuccess }, ref) => {
  const [isLoading, setIsLoading] = useState(false);
  const [tool, setTool] = useState<Tools>();
  const [open, setOpen] = useState(false);

  useImperativeHandle(ref, () => ({
    showConfig: tool => {
      setTool(tool);
      setOpen(true);
    },
  }));

  const formSchema = generateZodSchema(tool?.envSchema);
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: generateDefaultValues(tool?.envSchema),
  });

  const onSubmit = async (values: z.infer<typeof formSchema>) => {
    try {
      setIsLoading(true);
      await installTool({
        toolId: tool!.id,
        env: values,
      });
      toast.success('Install success', {
        description: 'Tool config saved',
      });
      setOpen(false);
      onSuccess?.();
    } catch (error) {
      toast.error('Install failed', {
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (!tool) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Install {tool.name}</DialogTitle>
        </DialogHeader>
        <div className="mt-4 flex-1">
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
                          <Input
                            type={value.type === 'number' ? 'number' : 'text'}
                            placeholder={value.description}
                            {...field}
                            value={field.value ?? (value.type === 'number' ? 0 : '')}
                            onChange={e => {
                              const val = value.type === 'number' ? (e.target.value === '' ? 0 : Number(e.target.value)) : e.target.value;
                              field.onChange(val);
                            }}
                          />
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
        </div>
      </DialogContent>
    </Dialog>
  );
});

const generateZodSchema = (schema: Exclude<JSONSchema, boolean>) => {
  const zodSchema: Record<string, any> = {};
  if (schema?.properties) {
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

const generateDefaultValues = (schema?: Tools['envSchema']) => {
  const defaultValues: Record<string, any> = {};
  if (!schema?.properties) {
    return defaultValues;
  }

  Object.entries(schema.properties).forEach(([key, _propSchema]) => {
    const propSchema = _propSchema as PrismaJson.JsonSchema;
    if (typeof propSchema === 'boolean') {
      defaultValues[key] = false;
      return;
    }

    if (propSchema.default) {
      defaultValues[key] = propSchema.default;
      return;
    }

    switch (propSchema.type) {
      case 'string':
        defaultValues[key] = '';
        break;
      case 'number':
      case 'integer':
        defaultValues[key] = 0;
        break;
      case 'boolean':
        defaultValues[key] = false;
        break;
      case 'array':
        defaultValues[key] = [];
        break;
      case 'object':
        defaultValues[key] = {};
        break;
      case 'null':
      default:
        defaultValues[key] = null;
    }
  });
  return defaultValues;
};
