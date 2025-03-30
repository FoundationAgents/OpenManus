'use server';

import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';
import { decryptWithPrivateKey } from '@/lib/crypto';
import { LANGUAGE_CODES } from '@/lib/language';
import { prisma } from '@/lib/prisma';
import { to } from '@/lib/to';
import fs from 'fs';
import path, { parse } from 'path';

const API_BASE_URL = 'http://localhost:5172';

const privateKey = fs.readFileSync(path.join(process.cwd(), 'keys', 'private.pem'), 'utf8');

export const getTask = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ taskId: string }>) => {
  const { taskId } = args;
  const task = await prisma.tasks.findUnique({
    where: { id: taskId, organizationId: organization.id },
    include: { progresses: { orderBy: { index: 'asc' } } },
  });
  return task;
});

export const pageTasks = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ page: number; pageSize: number }>) => {
  const { page = 1, pageSize = 10 } = args || {};
  const tasks = await prisma.tasks.findMany({
    where: { organizationId: organization.id },
    skip: (page - 1) * pageSize,
    take: pageSize,
    orderBy: { createdAt: 'desc' },
  });
  const total = await prisma.tasks.count();
  return { tasks, total };
});

export const createTask = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ prompt: string }>) => {
  const { prompt } = args;
  const llmConfig = await prisma.llmConfigs.findFirst({
    where: {
      type: 'default',
      organizationId: organization.id,
    },
  });

  const preferences = await prisma.preferences.findUnique({
    where: { organizationId: organization.id },
  });

  // Create task
  const task = await prisma.tasks.create({
    data: {
      prompt,
      status: 'pending',
      llmId: llmConfig?.id || '',
      organizationId: organization.id,
    },
  });

  // Send task to API
  const [error, response] = await to(
    fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        task_id: task.id,
        preferences: { language: LANGUAGE_CODES[preferences?.language as keyof typeof LANGUAGE_CODES] },
        llm_config: llmConfig
          ? {
              model: llmConfig.model,
              base_url: llmConfig.baseUrl,
              api_key: decryptWithPrivateKey(llmConfig.apiKey, privateKey),
              max_tokens: llmConfig.maxTokens,
              max_input_tokens: llmConfig.maxInputTokens,
              temperature: llmConfig.temperature,
              api_type: llmConfig.apiType,
              api_version: llmConfig.apiVersion,
            }
          : null,
      }),
    }).then(res => res.json() as Promise<{ task_id: string }>),
  );

  if (error || !response) {
    await prisma.tasks.update({ where: { id: task.id }, data: { status: 'failed' } });
    throw new Error('Failed to create task');
  }

  await prisma.tasks.update({ where: { id: task.id }, data: { outId: response.task_id, status: 'processing' } });

  // Handle event stream in background
  handleTaskEvents(task.id, response.task_id, organization.id).catch(error => {
    console.error('Failed to handle task events:', error);
  });

  return { id: task.id, outId: response.task_id };
});

// Handle event stream in background
async function handleTaskEvents(taskId: string, outId: string, organizationId: string) {
  const streamResponse = await fetch(`${API_BASE_URL}/tasks/${outId}/events`);
  const reader = streamResponse.body?.getReader();
  if (!reader) throw new Error('Failed to get response stream');

  const decoder = new TextDecoder();
  let messageIndex = 0;
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (value) {
        buffer += decoder.decode(value, { stream: true });
      }

      const lines = buffer.split('\n');
      // Keep the last line (might be incomplete) if not the final read
      buffer = done ? '' : lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

        try {
          const parsed = JSON.parse(line.slice(6));
          const { event_name, step, content } = parsed;

          // Write message to database
          await prisma.taskProgresses.create({
            data: { taskId, organizationId, index: messageIndex++, step, type: event_name, content },
          });

          // If complete message, update task status
          if (event_name === 'agent:lifecycle:complete') {
            await prisma.tasks.update({
              where: { id: taskId },
              data: { status: 'completed' },
            });
            return;
          }
        } catch (error) {
          console.error('Failed to process message:', error);
        }
      }

      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}
