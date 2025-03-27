import { useEffect, useState } from 'react';
import useWebSocket from 'react-use-websocket';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseTaskWebSocketProps {
  taskId: string;
  outId?: string;
}

interface WebSocketMessage {
  type: string;
  data:
    | {
        screenshot: string;
        content: string;
      }
    | string;
  message?: string;
}

export function useTaskWebSocket({ taskId, outId }: UseTaskWebSocketProps) {
  const [wsStatus, setWsStatus] = useState<WebSocketStatus>('disconnected');
  const [screenshot, setScreenshot] = useState<string | undefined>(undefined);

  const { lastMessage, readyState } = useWebSocket(outId ? `ws://localhost:5172/ws/${outId}` : null, {
    shouldReconnect: closeEvent => true,
    reconnectAttempts: 10,
    reconnectInterval: 3000,
    onOpen: () => setWsStatus('connected'),
    onClose: () => setWsStatus('disconnected'),
    onError: () => setWsStatus('error'),
  });

  useEffect(() => {
    if (lastMessage) {
      try {
        const message = JSON.parse(lastMessage.data) as WebSocketMessage;
        if (message.type === 'screenshot' && typeof message.data === 'object') {
          setScreenshot(message.data.screenshot);
        } else if (message.type === 'error') {
          console.error('WebSocket error from server:', message.message);
          setWsStatus('error');
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    }
  }, [lastMessage]);

  return {
    wsStatus,
    screenshot,
    isConnecting: wsStatus === 'connecting',
    isConnected: wsStatus === 'connected',
    isDisconnected: wsStatus === 'disconnected',
    isError: wsStatus === 'error',
  };
}
