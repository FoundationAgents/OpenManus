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
      <main className="relative h-full w-full overflow-hidden">{children}</main>
      <ConfigDialog />
    </SidebarProvider>
  );
}
