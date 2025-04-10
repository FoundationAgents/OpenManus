'use client';
import { getToolsInfo } from '@/actions/tools';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Info, Settings, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import Markdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ToolConfigForm } from './tool-config-form';
import { Button } from '@/components/ui/button';

export default function MarketplacePage() {
  const [allTools, setAllTools] = useState<NonNullable<Awaited<ReturnType<typeof getToolsInfo>>['data']>>([]);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [showConfig, setShowConfig] = useState(false);

  useEffect(() => {
    getToolsInfo({}).then(res => {
      const tools = res.data ?? [];
      setAllTools(tools);
    });
  }, []);

  const handleConfigSuccess = () => {
    getToolsInfo({}).then(res => {
      const tools = res.data ?? [];
      setAllTools(tools);
    });
    setShowConfig(false);
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
            className="group bg-card hover:border-primary/50 relative flex h-[140px] cursor-pointer flex-col justify-between rounded-lg border p-6 transition-all hover:scale-[1.02] hover:shadow-lg"
            onClick={() => setSelectedTool(tool.name)}
          >
            <div className="flex items-center justify-between">
              <span className="group-hover:text-primary line-clamp-1 text-lg font-semibold transition-colors">{tool.name}</span>
            </div>
            <p className="text-muted-foreground group-hover:text-foreground/80 line-clamp-2 text-sm transition-colors">{tool.description}</p>
          </div>
        ))}
      </div>

      {/* Detail Dialog */}
      <Dialog open={!!selectedTool} onOpenChange={open => !open && setSelectedTool(null)}>
        <DialogContent style={{ height: '800px', width: '1200px', maxWidth: 1200, overflowY: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{selectedTool}</DialogTitle>
            <div className="mt-2">
              <Button variant="default" size="sm" className="w-full sm:w-auto" onClick={() => setShowConfig(true)}>
                Install Tool
              </Button>
            </div>
          </DialogHeader>
          {selectedTool && (
            <div className="markdown-body text-wrap">
              <Markdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  a: ({ href, children }) => {
                    return (
                      <a href={href} target="_blank" rel="noopener noreferrer">
                        {children}
                      </a>
                    );
                  },
                }}
              >
                {allTools.find(t => t.name === selectedTool)?.description}
              </Markdown>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Config Dialog */}
      <Dialog open={showConfig} onOpenChange={setShowConfig}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Install {selectedTool}</DialogTitle>
          </DialogHeader>
          {selectedTool && (
            <div className="mt-4 flex-1">
              <ToolConfigForm tool={allTools.find(t => t.name === selectedTool)!} onSuccess={handleConfigSuccess} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
