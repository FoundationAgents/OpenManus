import { useRef, useState } from 'react';

interface UseAutoScrollOptions {
  threshold?: number;
  enabled?: boolean;
}

export function useAutoScroll(options: UseAutoScrollOptions = {}) {
  const { threshold = 10, enabled = true } = options;
  const [isNearBottom, setIsNearBottom] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const shouldAutoScroll = isNearBottom && enabled;

  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      const isNearBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < threshold;
      setIsNearBottom(isNearBottom);
    }
  };

  const scrollToBottom = () => {
    if (containerRef.current && shouldAutoScroll) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  };

  const scrollToBottomImmediate = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  };

  return {
    containerRef,
    isNearBottom,
    shouldAutoScroll,
    handleScroll,
    scrollToBottom,
    scrollToBottomImmediate,
  };
}
