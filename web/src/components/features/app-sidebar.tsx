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
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { create } from 'zustand';
import { useConfigDialog } from './config/config-dialog';
import { LogOutIcon, SettingsIcon, ChevronsUpDown } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '../ui/button';
import { getMe } from '@/actions/me';

export const useRecentTasks = create<{ tasks: Tasks[]; refreshTasks: () => Promise<void> }>(set => ({
  tasks: [],
  refreshTasks: async () => {
    const res = await pageTasks({ page: 1, pageSize: 30 });
    set({ tasks: res.data?.tasks || [] });
  },
}));

const useMeStore = create<{ me: Awaited<ReturnType<typeof getMe>>['data'] | null; refreshMe: () => Promise<void> }>(set => ({
  me: null,
  refreshMe: async () => {
    const res = await getMe({});
    if (res.error || !res.data) {
      throw new Error('Failed to fetch user data');
    }
    set({ me: res.data });
  },
}));

export function AppSidebar() {
  const router = useRouter();
  const { me, refreshMe } = useMeStore();
  const { tasks, refreshTasks } = useRecentTasks();
  const { show } = useConfigDialog();
  const pathname = usePathname();

  const currentTaskId = pathname.split('/').pop();

  useEffect(() => {
    refreshMe()
      .then(() => {
        refreshTasks();
      })
      .catch(error => {
        if (error?.message.startsWith('Authentication failed')) {
          document.cookie = 'token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
          router.push('/login');
        }
      });
  }, []);

  const handleLogout = () => {
    document.cookie = 'token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT';
    router.push('/login');
  };

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center justify-between">
          <span className="text-lg font-bold">{me?.organizationName || 'OpenManus'}</span>
          <Link href="https://github.com/iheytang/OpenManus" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" className="h-5 w-5 opacity-80" color="text-inherit" xmlns="http://www.w3.org/2000/svg">
              <title>GitHub</title>
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
          </Link>
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
      <SidebarFooter>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-16 w-full">
              <div className="flex h-16 w-full items-center gap-3">
                <Avatar className="h-6 w-6">
                  <AvatarFallback className="text-base">{me?.name ? me.name.charAt(0).toUpperCase() : '?'}</AvatarFallback>
                </Avatar>
                <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
                  <span className="truncate text-sm font-medium">{me?.name || me?.email}</span>
                  <span className="text-muted-foreground truncate text-xs">{me?.email}</span>
                </div>
                <ChevronsUpDown className="text-muted-foreground h-4 w-4 shrink-0" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-[200px]">
            <DropdownMenuItem onClick={show} className="py-2.5">
              <SettingsIcon className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="py-2.5">
              <LogOutIcon className="mr-2 h-4 w-4" />
              <span>Logout</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
