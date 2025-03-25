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
    const res = await pageTasks({ page: 1, pageSize: 10 });
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
      <SidebarFooter>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="w-full h-16">
              <div className="flex items-center gap-3 w-full h-16">
                <Avatar className="h-6 w-6">
                  <AvatarFallback className="text-base">{me?.name ? me.name.charAt(0).toUpperCase() : '?'}</AvatarFallback>
                </Avatar>
                <div className="flex flex-col items-start flex-1 min-w-0 gap-1">
                  <span className="text-sm font-medium truncate">{me?.name || me?.email}</span>
                  <span className="text-xs text-muted-foreground truncate">{me?.email}</span>
                </div>
                <ChevronsUpDown className="h-4 w-4 text-muted-foreground shrink-0" />
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
