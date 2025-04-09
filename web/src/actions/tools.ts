'use server';
import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';
import { JSONSchema } from 'json-schema-to-ts';
const MANUS_URL = process.env.MANUS_URL || 'http://localhost:5172';

export const getToolsInfo = withUserAuth(async ({}: AuthWrapperContext<{}>) => {
  const tools = (await fetch(`${MANUS_URL}/tools`).then(res => res.json())) as {
    name: string;
    type: 'tool' | 'mcp';
    description: string;
    parameters: JSONSchema;
  }[];

  return tools;
});
