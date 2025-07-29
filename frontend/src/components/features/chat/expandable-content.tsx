import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Markdown } from '@/components/block/markdown';
import { cn } from '@/libs/utils';

interface ExpandableContentProps {
  content: string;
  maxLength?: number;
  className?: string;
}

export function ExpandableContent({ 
  content, 
  maxLength = 500, 
  className 
}: ExpandableContentProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // 如果内容长度小于限制，直接显示完整内容
  if (content.length <= maxLength) {
    return (
      <div className={cn("flex flex-col gap-2 space-y-2", className)}>
        <Markdown className="chat">{content}</Markdown>
      </div>
    );
  }

  // 截断内容，在单词边界处截断
  const truncatedContent = content.substring(0, maxLength);
  const lastSpaceIndex = truncatedContent.lastIndexOf(' ');
  const displayContent = isExpanded 
    ? content 
    : (lastSpaceIndex > maxLength * 0.8 ? truncatedContent.substring(0, lastSpaceIndex) : truncatedContent) + '...';

  return (
    <div className={cn("flex flex-col gap-2 space-y-2", className)}>
      <Markdown className="chat">{displayContent}</Markdown>
      
      <div className="flex justify-start">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-auto p-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              收起
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              展开查看更多 ({Math.round((content.length - maxLength) / 100) * 100}+ 字符)
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
