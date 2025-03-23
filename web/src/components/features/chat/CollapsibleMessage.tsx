import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { cn } from '@/lib/utils';

interface CollapsibleMessageProps {
  title: string;
  content: string;
  badge?: React.ReactNode;
  defaultExpanded?: boolean;
  className?: string;
}

export const CollapsibleMessage = ({ title, content, badge, defaultExpanded = false, className = '' }: CollapsibleMessageProps) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className={className}>
      <div className="flex items-center gap-2 p-1 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
        )}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {badge}
          <span className="truncate text-sm">{title || ''}</span>
        </div>
      </div>
      {isExpanded && (
        <div className="pl-8 pr-2 pb-2 markdown-content overflow-auto">
          <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {content}
          </Markdown>
        </div>
      )}
    </div>
  );
};
