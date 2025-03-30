'use server';
import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';

const API_BASE_URL = 'http://localhost:5172';

export const getFileContent = withUserAuth(async ({ args }: AuthWrapperContext<{ path: string }>) => {
  const { path } = args;

  const response = await fetch(`${API_BASE_URL}/workspace/file?path=${path}`);
  const data = await response.text();
  return data;
});
