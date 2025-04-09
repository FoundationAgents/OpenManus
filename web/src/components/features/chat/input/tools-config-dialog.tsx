import { getToolsInfo } from '@/actions/tools';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useEffect, useState } from 'react';
import { Check, X, Info } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import Markdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { create } from 'zustand';

export const useSelectedTools = create<{
  selected: string[];
  setSelected: (selected: string[]) => void;
}>(set => ({
  selected: ['web_search', 'str_replace_editor', 'python_execute', 'browser_use'],
  setSelected: selected => set({ selected }),
}));

interface ToolsConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selected?: string[];
  onSelected?: (selected: string[]) => void;
}

export const ToolsConfigDialog = ({ open, onOpenChange, selected, onSelected }: ToolsConfigDialogProps) => {
  const [allTools, setAllTools] = useState<NonNullable<Awaited<ReturnType<typeof getToolsInfo>>['data']>>([]);
  const [showTool, setShowTool] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    getToolsInfo({}).then(res => {
      const tools = res.data ?? [];
      setAllTools(tools);
    });
  }, [open]);

  const handleToggleTool = (toolName: string) => {
    onSelected?.(selected?.includes(toolName) ? selected.filter(name => name !== toolName) : [...(selected ?? []), toolName]);
  };

  const handleShowToolInfo = (toolName: string) => {
    setShowTool(toolName);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent style={{ width: '90vw', maxWidth: '90vw', display: 'flex', flexDirection: 'column', height: '80vh', maxHeight: '80vh' }}>
          <DialogHeader>
            <DialogTitle>Tools Configuration</DialogTitle>
          </DialogHeader>

          <div className="flex h-full flex-1 flex-col gap-4">
            {/* Selected Tools Section */}
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Selected Tools</h3>
              <div className="flex flex-wrap gap-2">
                {selected?.map(toolName => {
                  const tool = allTools.find(t => t.name === toolName);
                  return (
                    <Badge key={toolName} variant="secondary" className="flex items-center gap-1">
                      {toolName}
                      <X className="hover:text-destructive h-3 w-3 cursor-pointer" onClick={() => handleToggleTool(toolName)} />
                    </Badge>
                  );
                })}
              </div>
            </div>

            {/* Available Tools Section */}
            <div className="grid flex-1 grid-cols-4 content-start items-start gap-4 overflow-y-auto">
              {allTools.map(tool => (
                <div
                  key={tool.name}
                  className={`group hover:bg-muted relative flex h-[80px] cursor-pointer flex-col justify-between rounded-md border p-2 transition-colors ${
                    selected?.includes(tool.name) ? 'border-primary bg-muted' : ''
                  }`}
                  onClick={() => handleShowToolInfo(tool.name)}
                >
                  <div className="flex items-center justify-between">
                    <span className="line-clamp-1 text-sm font-medium">{tool.name}</span>
                    <div className="flex items-center gap-2">
                      {tool.type === 'mcp' && <Badge variant="secondary">MCP</Badge>}
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Info
                              className="text-muted-foreground hover:text-foreground h-4 w-4 cursor-pointer"
                              onClick={() => handleShowToolInfo(tool.name)}
                            />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Click to view details</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      <Checkbox
                        onClick={e => {
                          e.stopPropagation();
                        }}
                        checked={selected?.includes(tool.name)}
                        onCheckedChange={() => handleToggleTool(tool.name)}
                        className="h-4 w-4"
                      />
                    </div>
                  </div>
                  <p className="text-muted-foreground line-clamp-2 text-xs">{tool.description}</p>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Tool Info Dialog */}
      <Dialog open={!!showTool} onOpenChange={open => !open && setShowTool(null)}>
        <DialogContent style={{ height: '500px', overflowY: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <DialogHeader className="h-12">
            <DialogTitle>{showTool}</DialogTitle>
          </DialogHeader>
          {showTool && (
            <div className="flex-1 space-y-4 overflow-y-auto">
              <div>
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
                    {allTools.find(t => t.name === showTool)?.description}
                  </Markdown>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
