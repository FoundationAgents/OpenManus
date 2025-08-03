import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MoreHorizontal, Trash2 } from 'lucide-react';
import { cn } from '@/libs/utils';
import { type Task, useRecentTasks } from '@/hooks/use-tasks';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';


interface TaskItemProps {
  task: Task;
}

export function TaskItem({ task }: TaskItemProps) {
  const location = useLocation();
  const { deleteTask } = useRecentTasks();
  const [isDeleting, setIsDeleting] = useState(false);

  const currentTaskId = location.pathname.split('/').pop();
  const isActive = currentTaskId === task.id;

  // 处理删除任务
  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const confirmed = window.confirm(`确定要删除任务"${task.request}"吗？此操作无法撤销。`);

    if (confirmed) {
      setIsDeleting(true);
      try {
        await deleteTask(task.id);
      } catch (error) {
        console.error('Failed to delete task:', error);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  // 截断长文本
  const truncateText = (text: string, maxLength: number = 30) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className={cn(
      'group relative flex items-center gap-2 rounded-md p-2 text-sm transition-colors hover:bg-accent',
      isActive && 'bg-accent'
    )}>
      <Link
        to={`/tasks/${task.id}`}
        className="flex-1 min-w-0"
      >
        <span className="font-medium truncate" title={task.request}>
          {truncateText(task.request)}
        </span>
      </Link>

      {/* 操作菜单 */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={(e) => e.preventDefault()}
          >
            <MoreHorizontal className="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-32">
          <DropdownMenuItem
            onClick={handleDelete}
            disabled={isDeleting}
            className="text-red-600 focus:text-red-600"
          >
            <Trash2 className="h-3 w-3 mr-2" />
            {isDeleting ? '删除中...' : '删除'}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
