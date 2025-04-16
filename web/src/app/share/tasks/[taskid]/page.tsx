'use client';

import { getSharedTask } from '@/actions/tasks';
import { ChatMessages } from '@/components/features/chat/messages';
import { ChatPreview } from '@/components/features/chat/preview';
import { usePreviewData } from '@/components/features/chat/preview/store';
import { aggregateMessages } from '@/lib/chat-messages';
import { Message } from '@/lib/chat-messages/types';
import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export default function ChatSharePage() {
  const params = useParams();
  const taskId = params.taskid as string;

  const { setData: setPreviewData } = usePreviewData();
  const [isNearBottom, setIsNearBottom] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesQueueRef = useRef<Message[]>([]);
  const timeoutIdRef = useRef<NodeJS.Timeout | null>(null);

  const shouldAutoScroll = true || isNearBottom;

  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isNearBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
      setIsNearBottom(isNearBottom);
    }
  };

  const scrollToBottom = () => {
    if (messagesContainerRef.current && shouldAutoScroll) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  const processMessageQueue = () => {
    if (messagesQueueRef.current.length > 0) {
      const nextMessage = messagesQueueRef.current.shift();

      setMessages(prevMessages => [...prevMessages, nextMessage!]);
      if (shouldAutoScroll) {
        if (nextMessage?.type === 'agent:lifecycle:step:think:browser:browse:complete') {
          setPreviewData({
            type: 'browser',
            url: nextMessage.content.url,
            title: nextMessage.content.title,
            screenshot: nextMessage.content.screenshot,
          });
        }
        if (nextMessage?.type === 'agent:lifecycle:step:act:tool:execute:start') {
          setPreviewData({ type: 'tool', toolId: nextMessage.content.id });
        }
      }

      if (messagesQueueRef.current.length > 0) {
        timeoutIdRef.current = setTimeout(processMessageQueue, 200);
      }
    }
  };

  const refreshTask = async () => {
    const res = await getSharedTask({ taskId });
    if (res.error || !res.data) {
      console.error('Error fetching task:', res.error);
      return;
    }

    setMessages([]);
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
      timeoutIdRef.current = null;
    }

    messagesQueueRef.current = res.data.progresses.map(step => ({
      ...step,
      index: step.index! || 0,
      type: step.type as any,
      role: 'assistant' as const,
    }));

    if (messagesQueueRef.current.length > 0) {
      timeoutIdRef.current = setTimeout(processMessageQueue, 500);
    }

    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
    }
  };

  useEffect(() => {
    if (!taskId) return;
    refreshTask();

    return () => {
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
      }
    };
  }, [taskId]);

  useEffect(() => {
    if (shouldAutoScroll) {
      requestAnimationFrame(scrollToBottom);
    }
  }, [messages, shouldAutoScroll]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (timeoutIdRef.current) {
        clearTimeout(timeoutIdRef.current);
      }
    };
  }, []);

  return (
    <div className="flex h-screen w-full flex-row justify-between">
      <div className="flex-1">
        <div className="relative flex h-screen flex-col">
          <div
            ref={messagesContainerRef}
            className="flex-3/5 space-y-4 overflow-y-auto p-4 pb-60"
            style={{
              scrollBehavior: 'smooth',
              overscrollBehavior: 'contain',
            }}
            onScroll={handleScroll}
          >
            <ChatMessages messages={aggregateMessages(messages)} />
          </div>
        </div>
      </div>
      <div className="min-w-[800px] flex-1 items-center justify-center p-2">
        <ChatPreview taskId={taskId} messages={messages} />
      </div>
    </div>
  );
}
