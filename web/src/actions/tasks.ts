'use server';

import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';
import { prisma } from '@/lib/prisma';
import { to } from '@/lib/to';
import { Message } from '@/types/chat';

const API_BASE_URL = 'http://localhost:5172';

export const getTask = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ taskId: string }>) => {
  const { taskId } = args;
  const task = await prisma.tasks.findUnique({
    where: { id: taskId, organizationId: organization.id },
    include: { steps: true },
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

  const task = await prisma.tasks.create({ data: { prompt, status: 'pending', llmId: llmConfig?.id || '', organizationId: organization.id } });

  const [error, response] = await to(
    fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        llm_config: llmConfig
          ? {
              model: llmConfig.model,
              base_url: llmConfig.baseUrl,
              api_key: llmConfig.apiKey,
              max_tokens: llmConfig.maxTokens,
              max_input_tokens: llmConfig.maxInputTokens,
              temperature: llmConfig.temperature,
              api_type: llmConfig.apiType,
              api_version: llmConfig.apiVersion,
            }
          : null,
      }),
    }).then(res => res.json() as Promise<{ task_id: string }>)
  );

  if (error || !response) {
    await prisma.tasks.update({ where: { id: task.id }, data: { status: 'failed' } });
    throw new Error('Failed to create task');
  }

  await prisma.tasks.update({ where: { id: task.id }, data: { outId: response.task_id, status: 'processing' } });

  let storedMessages: Message[] = [];
  let messageQueue: Message[] = [];
  let isProcessing = false;

  const processMessageQueue = async () => {
    if (isProcessing || messageQueue.length === 0) return;

    isProcessing = true;
    try {
      const currentQueue = [...messageQueue];
      messageQueue = [];

      await prisma.taskProcesses.createMany({
        data: currentQueue.map((message, index) => ({
          taskId: task.id,
          organizationId: organization.id,
          index: index + storedMessages.length,
          result: message.content,
          type: message.type ?? 'unknown',
          step: message.step ?? 0,
        })),
      });
      if (currentQueue[currentQueue.length - 1].content.startsWith("🎯 Tool 'terminate' completed its mission!")) {
        const success = currentQueue[currentQueue.length - 1].content.trim().endsWith('success');
        await prisma.tasks.update({ where: { id: task.id }, data: { status: success ? 'completed' : 'failed' } });
      }

      storedMessages = [...storedMessages, ...currentQueue];
    } finally {
      isProcessing = false;
    }
  };

  handleTaskEventsStreamResponse(response.task_id, async messages => {
    if (messages.length > messageQueue.length) {
      const newProcesses = messages.slice(messageQueue.length);
      console.log('newProcesses', newProcesses.length);
      messageQueue = [...newProcesses];
      await processMessageQueue();
    }
  });

  return { id: task.id, outId: response.task_id };
});

const handleTaskEventsStreamResponse = async (taskId: string, onMessage: (messages: Message[]) => void) => {
  const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/events`);

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Failed to get response stream');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            break;
          }
          try {
            const parsed = JSON.parse(data);
            // only handle status event, any status event contains all steps info
            if (parsed.type === 'status') {
              onMessage(
                parsed.steps.map((step: { step: number; result: string; type: string }) => ({
                  role: 'assistant' as const,
                  content: step.result,
                  type: step.type,
                  step: step.step,
                }))
              );
            }
          } catch (error) {
            console.error('Failed to parse response data:', error);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};
