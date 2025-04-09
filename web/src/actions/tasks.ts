'use server';

import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';
import { decryptWithPrivateKey } from '@/lib/crypto';
import { LANGUAGE_CODES } from '@/lib/language';
import { prisma } from '@/lib/prisma';
import { to } from '@/lib/to';
import fs from 'fs';
import path from 'path';

const MANUS_URL = process.env.MANUS_URL || 'http://localhost:5172';

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

export const createTask = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ prompt: string; tools: string[]; files: File[] }>) => {
  const { prompt, tools, files } = args;
  const llmConfig = await prisma.llmConfigs.findFirst({
    where: {
      type: 'default',
      organizationId: organization.id,
    },
  });

  if (!llmConfig) throw new Error('LLM config not found');

  const preferences = await prisma.preferences.findUnique({
    where: { organizationId: organization.id },
  });

  // Create task
  const task = await prisma.tasks.create({
    data: {
      prompt,
      status: 'pending',
      llmId: llmConfig.id,
      organizationId: organization.id,
      tools,
    },
  });

  const formData = new FormData();
  formData.append('task_id', `${organization.id}/${task.id}`);
  formData.append('prompt', prompt);
  tools.forEach(tool => formData.append('tools', tool));
  formData.append('preferences', JSON.stringify({ language: LANGUAGE_CODES[preferences?.language as keyof typeof LANGUAGE_CODES] }));
  formData.append(
    'llm_config',
    JSON.stringify({
      model: llmConfig.model,
      base_url: llmConfig.baseUrl,
      api_key: decryptWithPrivateKey(llmConfig.apiKey, privateKey),
      max_tokens: llmConfig.maxTokens,
      max_input_tokens: llmConfig.maxInputTokens,
      temperature: llmConfig.temperature,
      api_type: llmConfig.apiType || '',
      api_version: llmConfig.apiVersion || '',
    }),
  );
  files.forEach(file => formData.append('files', file, file.name));

  const [error, response] = await to(
    fetch(`${MANUS_URL}/tasks`, {
      method: 'POST',
      body: formData,
    }).then(res => res.json() as Promise<{ task_id: string }>),
  );

  if (error || !response.task_id) {
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

export const restartTask = withUserAuth(
  async ({ organization, args }: AuthWrapperContext<{ taskId: string; prompt: string; tools: string[]; files: File[] }>) => {
    const { taskId, prompt, tools, files } = args;

    const llmConfig = await prisma.llmConfigs.findFirst({
      where: {
        type: 'default',
        organizationId: organization.id,
      },
    });

    if (!llmConfig) throw new Error('LLM config not found');

    const preferences = await prisma.preferences.findUnique({
      where: { organizationId: organization.id },
    });

    const task = await prisma.tasks.findUnique({ where: { id: taskId, organizationId: organization.id } });
    if (!task) throw new Error('Task not found');
    if (task.status !== 'completed' && task.status !== 'terminated' && task.status !== 'failed') throw new Error('Task is processing');

    const progresses = await prisma.taskProgresses.findMany({
      where: { taskId: task.id, type: { in: ['agent:lifecycle:start', 'agent:lifecycle:complete'] } },
      select: { type: true, content: true },
      orderBy: { index: 'asc' },
    });

    const history = progresses.reduce(
      (acc, progress) => {
        if (progress.type === 'agent:lifecycle:start') {
          acc.push({ role: 'user', message: (progress.content as { request: string }).request });
        } else if (progress.type === 'agent:lifecycle:complete') {
          const latestUserProgress = acc.findLast(item => item.role === 'user');
          if (latestUserProgress) {
            acc.push({ role: 'assistant', message: (progress.content as { results: string[] }).results.join('\n') });
          }
        }
        return acc;
      },
      [] as { role: string; message: string }[],
    );

    // Send task to API
    const formData = new FormData();
    formData.append('task_id', `${organization.id}/${task.id}`);
    formData.append('prompt', prompt);
    tools.forEach(tool => formData.append('tools', tool));
    formData.append('preferences', JSON.stringify({ language: LANGUAGE_CODES[preferences?.language as keyof typeof LANGUAGE_CODES] }));
    formData.append(
      'llm_config',
      JSON.stringify({
        model: llmConfig.model,
        base_url: llmConfig.baseUrl,
        api_key: decryptWithPrivateKey(llmConfig.apiKey, privateKey),
        max_tokens: llmConfig.maxTokens,
        max_input_tokens: llmConfig.maxInputTokens,
        temperature: llmConfig.temperature,
        api_type: llmConfig.apiType || '',
        api_version: llmConfig.apiVersion || '',
      }),
    );
    formData.append('history', JSON.stringify(history));
    files.forEach(file => formData.append('files', file));

    const [error, response] = await to(
      fetch(`${MANUS_URL}/tasks/restart`, {
        method: 'POST',
        body: formData,
      }).then(res => res.json() as Promise<{ task_id: string }>),
    );

    if (error || !response.task_id) {
      throw new Error('Failed to restart task');
    }

    await prisma.tasks.update({ where: { id: task.id }, data: { outId: response.task_id, status: 'processing' } });

    // Handle event stream in background
    handleTaskEvents(task.id, response.task_id, organization.id).catch(error => {
      console.error('Failed to handle task events:', error);
    });

    return { id: task.id, outId: response.task_id };
  },
);

export const terminateTask = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ taskId: string }>) => {
  const { taskId } = args;

  const task = await prisma.tasks.findUnique({ where: { id: taskId, organizationId: organization.id } });
  if (!task) throw new Error('Task not found');
  if (task.status !== 'processing' && task.status !== 'terminating') {
    return;
  }

  const [error] = await to(
    fetch(`${MANUS_URL}/tasks/terminate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: `${organization.id}/${taskId}` }),
    }),
  );
  if (error && error.message !== 'Task not found') throw new Error('Failed to terminate task');

  await prisma.tasks.update({ where: { id: taskId, organizationId: organization.id }, data: { status: 'terminated' } });
});

// Handle event stream in background
async function handleTaskEvents(taskId: string, outId: string, organizationId: string) {
  const streamResponse = await fetch(`${MANUS_URL}/tasks/${outId}/events`);
  const reader = streamResponse.body?.getReader();
  if (!reader) throw new Error('Failed to get response stream');

  const decoder = new TextDecoder();

  const taskProgresses = await prisma.taskProgresses.findMany({ where: { taskId }, orderBy: { index: 'asc' } });
  const rounds = taskProgresses.map(progress => progress.round);
  const round = Math.max(...rounds, 1);
  let messageIndex = taskProgresses.length || 0;
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
            data: { taskId, organizationId, index: messageIndex++, step, round, type: event_name, content },
          });

          // If complete message, update task status
          if (event_name === 'agent:lifecycle:complete') {
            await prisma.tasks.update({
              where: { id: taskId },
              data: { status: 'completed' },
            });
            return;
          }
          if (event_name === 'agent:lifecycle:terminating') {
            await prisma.tasks.update({
              where: { id: taskId },
              data: { status: 'terminating' },
            });
          }
          if (event_name === 'agent:lifecycle:terminated') {
            await prisma.tasks.update({
              where: { id: taskId },
              data: { status: 'terminated' },
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
