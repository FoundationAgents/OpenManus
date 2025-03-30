import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getBase64ImageUrl } from '@/lib/image';
import { Message } from '@/types/chat';
import { Terminal } from 'lucide-react';
import Markdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { useEffect, useState } from 'react';
import { getFileContent } from '@/actions/workspace';

const BrowserPagePreview = ({ message }: { message: Message }) => {
  return <img src={getBase64ImageUrl(message.content.screenshot)} alt="Manus's Computer Screen" className="w-full" />;
};

const NotPreview = () => {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="animate-pulse text-gray-500">Manus is not using the computer right now...</div>
    </div>
  );
};

const StrReplaceEditorPreview = ({ message }: { message: Message }) => {
  return (
    <div className="markdown-body p-4">
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          a: ({ node, ...props }) => {
            return <a {...props} target="_blank" />;
          },
        }}
      >
        {message.content.args.file_text}
      </Markdown>
    </div>
  );
};

const StrReplaceEditorViewPreview = ({ message }: { message: Message }) => {
  const [fileContent, setFileContent] = useState('');

  useEffect(() => {
    const path = message.content.args.path;
    if (!path) {
      return;
    }
    getFileContent({ path }).then(data => {
      setFileContent(data.data || '');
    });
  }, [message.content.args.path]);

  return (
    <div className="markdown-body p-4">
      <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
        {fileContent}
      </Markdown>
    </div>
  );
};

const PythonExecuteScriptPreview = ({ message }: { message: Message }) => {
  return <SyntaxHighlighter language="python">{message.content.args.code.trim()}</SyntaxHighlighter>;
};

const PythonExecuteResultPreview = ({ message }: { message: Message }) => {
  return <SyntaxHighlighter language="json">{message.content.result.trim()}</SyntaxHighlighter>;
};

const PreviewContent = ({ message }: { message: Message }) => {
  if (message?.type === 'agent:browser:browse:complete') {
    return <BrowserPagePreview message={message} />;
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'str_replace_editor' && message.content.args.command === 'view') {
    return <StrReplaceEditorViewPreview message={message} />;
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'str_replace_editor') {
    return <StrReplaceEditorPreview message={message} />;
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'python_execute') {
    return <PythonExecuteScriptPreview message={message} />;
  }
  if (message?.type === 'agent:tool:execute:complete' && message.content.name === 'python_execute') {
    return <PythonExecuteResultPreview message={message} />;
  }

  return <NotPreview />;
};

const PreviewDescription = ({ message }: { message: Message }) => {
  if (message?.type === 'agent:browser:browse:complete') {
    return (
      <CardDescription className="text-sm">
        Manus is browsing the page{' '}
        <a href={message.content.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
          <code>{message.content.url}</code>
        </a>
      </CardDescription>
    );
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'str_replace_editor' && message.content.args.command === 'view') {
    return (
      <CardDescription className="text-sm">
        Manus is using the computer to view the file <code>{message.content.args.path}</code>
      </CardDescription>
    );
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'str_replace_editor') {
    return (
      <CardDescription className="text-sm">
        Manus is using the computer to edit the file <code>{message.content.args.path}</code>
      </CardDescription>
    );
  }
  if (message?.type === 'agent:tool:execute:start' && message.content.name === 'python_execute') {
    return <CardDescription className="text-sm">Manus is running a Python script...</CardDescription>;
  }
  if (message?.type === 'agent:tool:execute:complete' && message.content.name === 'python_execute') {
    return <CardDescription className="text-sm">Manus has finished running the Python script.</CardDescription>;
  }
  return <CardDescription className="text-sm">Manus is not using the computer right now...</CardDescription>;
};

export const ChatPreview = ({ message }: { message: Message }) => {
  return (
    <Card className="flex h-full flex-col gap-0 px-2">
      <CardHeader className="flex-none p-2 py-1">
        <CardTitle className="text-normal">Manus's Computer</CardTitle>
        <PreviewDescription message={message} />
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-2">
        <div className="h-full w-full overflow-auto rounded-md">
          <PreviewContent message={message} />
        </div>
      </CardContent>
    </Card>
  );
};
