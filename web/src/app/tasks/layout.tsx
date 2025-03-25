'use client';

import { AppSidebar } from '@/components/features/app-sidebar';
import ConfigDialog from '@/components/features/config/config-dialog';
import { SidebarProvider } from '@/components/ui/sidebar';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="relative w-full h-full">{children}</main>
      <ConfigDialog />
    </SidebarProvider>
  );
}
