'use client';

import { AppSidebar } from '@/components/features/app-sidebar';
import ConfigDialog from '@/components/features/config/config-dialog';
import { SidebarProvider } from '@/components/ui/sidebar';
import useMe from '@/hooks/use-user';
import { useEffect } from 'react';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { refreshMe } = useMe();

  useEffect(() => {
    refreshMe();
  }, []);

  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="relative w-full h-full">{children}</main>
      <ConfigDialog />
    </SidebarProvider>
  );
}
