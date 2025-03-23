import { SidebarProvider } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/features/app-sidebar';

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="relative w-full h-full">{children}</main>
    </SidebarProvider>
  );
}
