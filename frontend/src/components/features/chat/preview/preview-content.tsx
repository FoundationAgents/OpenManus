import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useAsync } from '@/hooks/use-async';
import type { Message } from '@/libs/chat-messages';
import { getImageUrl } from '@/libs/image';
import { cn } from '@/libs/utils';
import { ChevronLeftIcon, ChevronDownIcon, ChevronUpIcon, DownloadIcon, FileIcon, FolderIcon, GlobeIcon, HomeIcon, LoaderIcon, PackageIcon, RefreshCwIcon } from 'lucide-react';
import { useState, useEffect } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { githubGist } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { usePreviewData } from './store';

export const PreviewContent = ({ messages }: { messages: Message[] }) => {
  const { data } = usePreviewData();

  if (data?.type === 'tool') {
    const executionStart = messages.find(m => m.type === 'tool.toolexecution' && m.content.execution_id === data.toolId);
    const executionComplete = messages.find(m => m.type === 'tool.toolresult' && m.content.execution_id === data.toolId);

    const name = executionStart?.content.tool_name;
    const args = executionStart?.content.parameters;
    const result = executionComplete?.content.result;
    const toolId = data.toolId;
    const isExecuting = executionStart && !executionComplete;

    return (
      <div className="h-full flex-col overflow-auto">
        <Popover>
          <PopoverTrigger>
            <Badge className="cursor-pointer font-mono text-xs">
              <div className="flex items-center gap-1">
                <PackageIcon className="h-3.5 w-3.5" />
                {name}
              </div>
            </Badge>
          </PopoverTrigger>
          <PopoverContent className="w-full">
            <code className="text-xs whitespace-nowrap">ID: {toolId}</code>
          </PopoverContent>
        </Popover>
        <div className="flex-1 space-y-4 p-2">
          {args && Object.keys(args).length > 0 && (
            <div className="space-y-2">
              <div className="text-muted-foreground text-sm font-medium">Parameters</div>
              <div className="bg-muted/40 space-y-2 rounded-md p-3">
                {Object.entries(args).map(([key, value]) => (
                  <div key={key} className="flex flex-col gap-1">
                    <div className="text-muted-foreground text-xs font-medium">{key}</div>
                    <Badge variant="outline" className="font-mono break-all whitespace-normal">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result ? (
            <div className="space-y-2">
              <div className="text-muted-foreground text-sm font-medium">Result</div>
              <ExpandableToolResult result={result} maxLines={10} maxLineLength={120} />
            </div>
          ) : (
            isExecuting && (
              <div className="space-y-2">
                <div className="text-muted-foreground text-sm font-medium">Result</div>
                <div className="bg-muted/40 flex items-center justify-center rounded-md p-6">
                  <div className="text-muted-foreground flex flex-col items-center gap-2">
                    <LoaderIcon className="h-5 w-5 animate-spin" />
                    <span className="text-xs">Processing...</span>
                  </div>
                </div>
              </div>
            )
          )}
        </div>
      </div>
    );
  }

  if (data?.type === 'browser') {
    return (
      <div className="h-full w-full overflow-hidden">
        <div className="mb-2 block w-fit max-w-full">
          <Badge className="max-w-full cursor-pointer font-mono text-xs">
            <div className="flex items-center justify-start gap-1 overflow-hidden">
              <GlobeIcon className="h-3.5 w-3.5" />
              <span className="flex-1 truncate">{data.url}</span>
            </div>
          </Badge>
        </div>
        <div className="h-full rounded-2xl border p-1">
          <div className="h-full w-full overflow-auto rounded-2xl">
            <img src={getImageUrl(data.screenshot)} alt="Manus's Computer Screen" className="h-auto w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (data?.type === 'workspace') {
    return <WorkspacePreview />;
  }

  return <NotPreview />;
};

const WorkspacePreview = () => {
  const { data, setData } = usePreviewData();
  const [isDownloading, setIsDownloading] = useState(false);

  const workspacePath = data?.type === 'workspace' ? data.path || '' : '';

  // 从路径中提取session_id（第一个路径段）
  const pathParts = workspacePath.split('/').filter(Boolean);
  const sessionId = pathParts.length > 0 ? pathParts[0] : '';
  const relativePath = pathParts.length > 1 ? pathParts.slice(1).join('/') : '';

  // Helper to check if we're in root directory
  const isRootDirectory = !relativePath;

  // Handle back button click - navigate to parent directory
  const handleBackClick = () => {
    if (isRootDirectory) return;

    const currentPathParts = relativePath.split('/').filter(Boolean);
    currentPathParts.pop(); // Remove the last path segment
    const parentRelativePath = currentPathParts.join('/');
    const newPath = sessionId + (parentRelativePath ? `/${parentRelativePath}` : '');

    setData({
      type: 'workspace',
      path: newPath,
    });
  };

  const handleItemClick = (item: { name: string; type: 'file' | 'directory' }) => {
    const newRelativePath = relativePath ? `${relativePath}/${item.name}` : item.name;
    const newPath = sessionId + (newRelativePath ? `/${newRelativePath}` : '');

    setData({
      type: 'workspace',
      path: newPath,
    });
  };

  const handleDownload = async () => {
    if (data?.type !== 'workspace') return;

    // 检查是否为空文件夹
    if (Array.isArray(workspace) && workspace.length === 0) {
      console.warn('Cannot download empty directory');
      return;
    }

    // 检查是否为文件夹（如果workspace是数组，说明是文件夹）
    const isDirectory = Array.isArray(workspace);

    setIsDownloading(true);
    try {
      // 统一的下载URL，后端会根据路径类型处理
      const downloadUrl = `/api/workspace/files?path=${encodeURIComponent(relativePath)}&download=true${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}`;

      // 创建下载链接
      const a = document.createElement('a');
      a.href = downloadUrl;

      // 设置下载文件名
      const fileName = relativePath.split('/').pop() || workspacePath.split('/').pop() || 'workspace';
      a.download = isDirectory ? `${fileName}.zip` : fileName;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    } finally {
      // Add a small delay to show loading state
      setTimeout(() => {
        setIsDownloading(false);
      }, 1000);
    }
  };

  // 添加刷新计数器用于强制重新获取数据
  const [refreshCounter, setRefreshCounter] = useState(0);

  const { data: workspace, isLoading } = useAsync(
    async () => {
      if (data?.type !== 'workspace') return;

      // 智能判断：根据路径是否有文件扩展名来决定处理方式
      const hasFileExtension = relativePath && /\.[^/.]+$/.test(relativePath);

      if (!hasFileExtension) {
        // 没有文件扩展名，很可能是目录，先尝试浏览目录
        try {
          const browseUrl = `/api/workspace/browse?path=${encodeURIComponent(relativePath)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}`;
          const browseRes = await fetch(browseUrl);
          if (browseRes.ok) {
            const browseData = await browseRes.json();
            return browseData.files.map((file: any) => ({
              name: file.name,
              type: file.type,
              size: file.size || 0,
              modifiedTime: file.modified || '',
              path: file.path
            }));
          } else if (browseRes.status === 400) {
            // 400错误通常表示路径不是目录，跳过错误日志
            console.debug('Path is not a directory, will try as file');
          } else {
            console.error('Error browsing directory:', browseRes.status, browseRes.statusText);
          }
        } catch (error) {
          console.error('Error browsing directory:', error);
        }
      }

      // 有文件扩展名或目录浏览失败，尝试获取文件内容
      try {
        const fileUrl = `/api/workspace/files?path=${encodeURIComponent(relativePath)}${sessionId ? `&session_id=${encodeURIComponent(sessionId)}` : ''}`;
        const fileRes = await fetch(fileUrl);
        if (fileRes.ok) {
          return await fileRes.blob();
        }
      } catch (error) {
        console.error('Error fetching file:', error);
      }

      return null;
    },
    [],
    {
      deps: [workspacePath, relativePath, sessionId, data?.type, refreshCounter],
    },
  );

  // 手动刷新函数
  const handleRefresh = () => {
    setRefreshCounter(prev => prev + 1);
  };

  // 监听文件系统事件进行实时更新
  useEffect(() => {
    if (data?.type !== 'workspace' || !sessionId) return;

    // 从全局获取事件处理器（假设在父组件中已经设置）
    const eventHandler = (window as any).eventHandler;
    if (!eventHandler) return;

    // 监听文件系统事件
    const handleFileSystemEvent = (event: any) => {
      console.log('📁 FileSystem event received:', event);

      // 检查事件是否属于当前session
      if (event.data?.session_id === sessionId) {
        // 文件系统发生变化，刷新当前视图
        setRefreshCounter(prev => prev + 1);
        console.log('🔄 Refreshing workspace view due to filesystem change');
      }
    };

    // 注册文件系统事件监听器
    eventHandler.on('filesystem.*', handleFileSystemEvent);

    // 清理函数
    return () => {
      eventHandler.off('filesystem.*', handleFileSystemEvent);
    };
  }, [data?.type, sessionId]);

  // 备用的定时刷新机制 - 每30秒检查一次（降低频率）
  useEffect(() => {
    if (data?.type !== 'workspace' || !sessionId) return;

    const interval = setInterval(() => {
      setRefreshCounter(prev => prev + 1);
    }, 30000); // 每30秒刷新一次作为备用

    return () => clearInterval(interval);
  }, [data?.type, sessionId]);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="flex flex-col items-center gap-2">
          <LoaderIcon className="text-primary h-5 w-5 animate-spin" />
          <span className="text-muted-foreground text-sm">Loading workspace...</span>
        </div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-muted-foreground">Could not load workspace content</div>
      </div>
    );
  }

  if (Array.isArray(workspace)) {
    return (
      <div className="p-4">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isRootDirectory ? (
                  <HomeIcon className="text-muted-foreground h-4 w-4" />
                ) : (
                  <Button variant="ghost" size="icon" onClick={handleBackClick} className="h-6 w-6" title="Return to parent directory">
                    <ChevronLeftIcon className="h-4 w-4" />
                  </Button>
                )}
                <CardTitle className="text-base">Workspace: {relativePath || `Session ${sessionId}`}</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleRefresh}
                  variant="outline"
                  size="sm"
                  title="Refresh directory"
                >
                  <RefreshCwIcon className="h-4 w-4" />
                </Button>
                <Button
                  onClick={handleDownload}
                  variant="outline"
                  size="sm"
                  disabled={isDownloading || (Array.isArray(workspace) && workspace.length === 0)}
                  title={Array.isArray(workspace) && workspace.length === 0 ? "Cannot download empty directory" : Array.isArray(workspace) ? "Download directory as ZIP" : "Download file"}
                >
                  {isDownloading ? (
                    <>
                      <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <DownloadIcon className="mr-2 h-4 w-4" />
                      Download
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {workspace.length === 0 ? (
                <div className="text-muted-foreground py-4 text-center">This directory is empty</div>
              ) : (
                workspace.map(item => (
                  <div
                    key={item.name}
                    className="hover:bg-muted/40 flex cursor-pointer items-center justify-between rounded-md border p-2"
                    onClick={() => handleItemClick(item)}
                  >
                    <div className="flex items-center gap-2">
                      {item.type === 'directory' ? <FolderIcon className="h-4 w-4 text-blue-500" /> : <FileIcon className="h-4 w-4 text-gray-500" />}
                      <span className="text-sm font-medium">{item.name}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-muted-foreground text-xs">{formatFileSize(item.size)}</span>
                      <span className="text-muted-foreground text-xs">{new Date(item.modifiedTime).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isRootDirectory ? (
                <HomeIcon className="text-muted-foreground h-5 w-5" />
              ) : (
                <Button variant="ghost" size="icon" onClick={handleBackClick} className="h-6 w-6" title="Return to parent directory">
                  <ChevronLeftIcon className="h-4 w-4" />
                </Button>
              )}
              <CardTitle className="text-base">File: {relativePath || sessionId}</CardTitle>
            </div>
            <Button onClick={handleDownload} variant="outline" size="sm" disabled={isDownloading} title="Download file">
              {isDownloading ? (
                <>
                  <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
                  Downloading...
                </>
              ) : (
                <>
                  <DownloadIcon className="mr-2 h-4 w-4" />
                  Download
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-md border">
            {workspace instanceof Blob &&
              (workspace.type.includes('image') || (data?.type === 'workspace' && data.path?.match(/\.(jpg|jpeg|png|gif|bmp|svg|webp)$/i))) ? (
              <img
                src={URL.createObjectURL(workspace)}
                alt={data?.type === 'workspace' ? data.path || 'File preview' : 'File preview'}
                className="h-auto w-full object-contain"
              />
            ) : workspace instanceof Blob ? (
              <FileContent blob={workspace} path={data?.type === 'workspace' ? data.path : ''} />
            ) : (
              <div className="text-muted-foreground p-4 text-center">This file type cannot be previewed</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const FileContent = ({ blob, path }: { blob: Blob; path: string }) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const { data: content, isLoading } = useAsync(
    async () => {
      return await blob.text();
    },
    [],
    { deps: [blob] },
  );

  // File download function
  const handleDownload = () => {
    setIsDownloading(true);
    try {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = path.split('/').pop() || 'download';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
    } finally {
      // Add a small delay to show loading state
      setTimeout(() => {
        setIsDownloading(false);
      }, 1000);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <LoaderIcon className="text-primary h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (!content) {
    return <div className="text-muted-foreground p-4 text-center">Could not load file content</div>;
  }

  // For binary files or very large files, show a simplified view
  if (content.length > 100000 || /[\x00-\x08\x0e-\x1f]/.test(content.substring(0, 1000))) {
    return (
      <div className="p-4 text-center">
        <p className="text-muted-foreground mb-2">File is too large or contains binary content</p>
        <Button onClick={handleDownload} disabled={isDownloading}>
          {isDownloading ? (
            <>
              <LoaderIcon className="mr-2 h-4 w-4 animate-spin" />
              Downloading...
            </>
          ) : (
            'Download'
          )}
        </Button>
      </div>
    );
  }

  const language = getFileLanguage(path);
  return (
    <SyntaxHighlighter
      language={language}
      showLineNumbers
      style={githubGist}
      customStyle={{
        fontSize: '0.875rem',
        lineHeight: '1.5',
        margin: 0,
        borderRadius: 0,
        maxHeight: '500px',
      }}
    >
      {content}
    </SyntaxHighlighter>
  );
};

// Format file size helper function
const formatFileSize = (size: number): string => {
  if (size < 1024) return `${size} B`;
  const kbSize = size / 1024;
  if (kbSize < 1024) return `${Math.round(kbSize)} KB`;
  const mbSize = kbSize / 1024;
  return `${mbSize.toFixed(1)} MB`;
};

const NotPreview = () => {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-pulse text-gray-500">Manus is not using the computer right now...</div>
    </div>
  );
};

// 可展开的工具结果显示组件
const ExpandableToolResult = ({ result, maxLines = 20, maxLineLength = 120 }: {
  result: string;
  maxLines?: number;
  maxLineLength?: number;
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // 处理长行截断的函数
  const processLongLines = (content: string, maxLength: number): string => {
    return content.split('\n').map(line => {
      if (line.length <= maxLength) {
        return line;
      }
      // 对于过长的行，在合适的位置截断并添加换行
      const chunks = [];
      for (let i = 0; i < line.length; i += maxLength) {
        chunks.push(line.substring(i, i + maxLength));
      }
      return chunks.join('\n');
    }).join('\n');
  };

  // 按行分割内容
  const lines = result.split('\n');

  // 检查是否需要截断（行数超限或有长行）
  const hasLongLines = lines.some(line => line.length > maxLineLength);
  const needsTruncation = lines.length > maxLines || hasLongLines;

  // 如果不需要截断，直接显示完整内容
  if (!needsTruncation) {
    return (
      <div className={cn('bg-muted/40 text-foreground overflow-hidden rounded-md')}>
        <SyntaxHighlighter
          language="json"
          showLineNumbers
          style={githubGist}
          customStyle={{
            color: 'inherit',
            backgroundColor: 'inherit',
            fontSize: '0.75rem',
            lineHeight: '1.5',
            margin: 0,
            borderRadius: 0,
            padding: '1rem 0.8rem',
            wordBreak: 'break-all',
            whiteSpace: 'pre-wrap',
          }}
        >
          {result}
        </SyntaxHighlighter>
      </div>
    );
  }

  // 处理显示内容
  let displayContent: string;
  if (isExpanded) {
    // 展开状态：处理长行但显示所有内容
    displayContent = processLongLines(result, maxLineLength);
  } else {
    // 收起状态：限制行数并处理长行
    const truncatedLines = lines.slice(0, maxLines);
    const truncatedContent = truncatedLines.join('\n');
    displayContent = processLongLines(truncatedContent, maxLineLength) + '\n...';
  }

  return (
    <div className="space-y-2">
      <div className={cn('bg-muted/40 text-foreground overflow-hidden rounded-md')}>
        <SyntaxHighlighter
          language="json"
          showLineNumbers
          style={githubGist}
          customStyle={{
            color: 'inherit',
            backgroundColor: 'inherit',
            fontSize: '0.75rem',
            lineHeight: '1.5',
            margin: 0,
            borderRadius: 0,
            padding: '1rem 0.8rem',
            wordBreak: 'break-all',
            whiteSpace: 'pre-wrap',
          }}
        >
          {displayContent}
        </SyntaxHighlighter>
      </div>

      <div className="flex justify-start">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-auto p-1 text-xs text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? (
            <>
              <ChevronUpIcon className="h-3 w-3 mr-1" />
              收起
            </>
          ) : (
            <>
              <ChevronDownIcon className="h-3 w-3 mr-1" />
              展开查看更多 ({lines.length > maxLines ? `${lines.length - maxLines} 行` : '长行内容'})
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

const getFileLanguage = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase();
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    java: 'java',
    c: 'c',
    cpp: 'cpp',
    cs: 'csharp',
    go: 'go',
    rb: 'ruby',
    php: 'php',
    swift: 'swift',
    kt: 'kotlin',
    rs: 'rust',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    html: 'html',
    css: 'css',
    scss: 'scss',
    less: 'less',
    json: 'json',
    yaml: 'yaml',
    yml: 'yaml',
    xml: 'xml',
    sql: 'sql',
    md: 'markdown',
    txt: 'text',
    log: 'text',
    ini: 'ini',
    toml: 'toml',
    conf: 'conf',
    env: 'env',
    dockerfile: 'dockerfile',
    'docker-compose': 'yaml',
    csv: 'csv',
  };
  return languageMap[ext || ''] || 'text';
};
