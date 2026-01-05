import { z } from 'zod';

export const mcpServerSchema = z
  .object({
    command: z.string().optional(),
    args: z.array(z.string()).optional(),
    env: z.record(z.string(), z.string()).optional(),
    url: z.string().url().optional(),
    headers: z.record(z.string(), z.string()).optional(),
    query: z.record(z.string(), z.string()).optional(),
  })
  .refine(data => {
    if (!data.command && !data.url) {
      return false;
    }
    if (data.command && data.url) {
      return false;
    }
    return true;
  }, 'Either command or url must be provided, but not both');
