'use client';

import { pageTasks } from '@/actions/tasks';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { cn } from '@/lib/utils';
import { Tasks } from '@prisma/client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { create } from 'zustand';

export const useRecentTasks = create<{ tasks: Tasks[]; refreshTasks: () => Promise<void> }>(set => ({
  tasks: [],
  refreshTasks: async () => {
    const res = await pageTasks();
    set({ tasks: res.data.tasks });
  },
}));

export function AppSidebar() {
  const { tasks, refreshTasks } = useRecentTasks();

  const pathname = usePathname();

  const currentTaskId = pathname.split('/').pop();

  useEffect(() => {
    refreshTasks();
  }, []);

  return (
    <Sidebar className="pl-2">
      <SidebarHeader>
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold">OpenManus</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Recent Tasks</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {tasks.map(item => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton asChild>
                    <Link href={`/tasks/${item.id}`} className={cn(currentTaskId === item.id && 'bg-gray-100')}>
                      <span>{item.prompt}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  );
}
