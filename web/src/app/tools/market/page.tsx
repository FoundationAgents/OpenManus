'use client';
import { getOrganizationToolsInfo, getToolsInfo } from '@/actions/tools';
import { Sparkles } from 'lucide-react';
import { useRef } from 'react';
import { ToolInfoDialog, ToolInfoDialogRef } from './tool-info-dialog';
import { useServerAction } from '@/hooks/use-async';

export default function MarketplacePage() {
  const { data: allTools = [], refresh: refreshAllTools } = useServerAction(getToolsInfo, {}, { cache: 'all-tools' });
  const { data: installedTools = [], refresh: refreshInstalledTools } = useServerAction(getOrganizationToolsInfo, {}, { cache: 'installed-tools' });

  const toolInfoDialogRef = useRef<ToolInfoDialogRef>(null);
  const handleConfigSuccess = () => {
    refreshAllTools();
    refreshInstalledTools();
  };

  return (
    <div className="container mx-auto py-8">
      <div className="mt-24 mb-24 flex flex-col items-center justify-center space-y-4">
        <div className="relative">
          <h1 className="relative z-10 bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-center text-4xl font-bold tracking-tight text-transparent">
            Tools Market
          </h1>
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 transform">
            <Sparkles className="h-8 w-8 animate-pulse text-yellow-400" />
          </div>
        </div>
        <p className="text-muted-foreground max-w-2xl text-center">Explore and install powerful tools to enhance your productivity</p>
      </div>

      {/* Available Tools Section */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {allTools.map(tool => (
          <div
            key={tool.name}
            className="group bg-card hover:border-primary/50 relative flex h-[140px] cursor-pointer flex-col justify-between rounded-lg border p-6 transition-all hover:scale-[1.01] hover:shadow-md"
            onClick={() => toolInfoDialogRef.current?.showInfo(tool)}
          >
            <div className="flex items-center justify-between">
              <span className="group-hover:text-primary line-clamp-1 text-lg font-semibold transition-colors">{tool.name}</span>
              {installedTools.some(installed => installed.id === tool.id) && (
                <span className="rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">Installed</span>
              )}
            </div>
            <p className="text-muted-foreground group-hover:text-foreground/80 line-clamp-2 text-sm transition-colors">{tool.description}</p>
          </div>
        ))}
      </div>

      <ToolInfoDialog ref={toolInfoDialogRef} onConfigSuccess={handleConfigSuccess} />
    </div>
  );
}
