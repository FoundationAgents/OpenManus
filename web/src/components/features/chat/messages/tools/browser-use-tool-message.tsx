import { useCurrentMessageIndex } from '@/app/tasks/hooks';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { getBase64ImageUrl } from '@/lib/image';
import { AggregatedMessage } from '@/types/chat';
import Link from 'next/link';

export const BrowserUseToolTooltip = ({
  args,
  result,
}: {
  args: any;
  result: {
    error: string | null;
    output: string;
    system: string | null;
    base64_image: string | null;
  };
}) => {
  if (!result) return null;

  const navigationMatch = result.output.match(/navigated to first result: ([^\s]+)/);
  const urlPattern = /All results:([\s\S]*)/;
  const allResults = result.output.match(urlPattern)
    ? result.output
        .match(urlPattern)![1]
        .split('\n')
        .map(url => url.trim())
    : [];
  const extractedFromPageMatch = result.output.match(/Extracted from page:\n([\s\S]*)/);
  const extractedFromPage = extractedFromPageMatch ? JSON.parse(extractedFromPageMatch[1]) : {};

  return (
    <div className="space-y-2">
      <div className="flex flex-col flex-wrap gap-2 text-wrap">
        {Object.entries(args).map(([key, value]) => (
          <div key={key} className="text-sm">
            <Badge variant="outline" className="cursor-pointer font-medium">
              {key}
            </Badge>
            <pre className="mt-1 ml-2 space-y-1 text-wrap">{typeof value === 'string' ? value : JSON.stringify(value)}</pre>
          </div>
        ))}
      </div>

      {allResults.length > 0 && (
        <div className="text-sm">
          <Badge variant="outline" className="font-medium">
            All results
          </Badge>
          <pre className="mt-1 ml-2 space-y-1 text-wrap">
            {allResults.map((url, index) => (
              <a key={index} href={url} target="_blank" rel="noopener noreferrer" className="block truncate text-blue-500 hover:underline">
                {url}
              </a>
            ))}
          </pre>
        </div>
      )}
      {navigationMatch && (
        <div className="text-sm">
          <Badge variant="outline" className="font-medium">
            Navigated to
          </Badge>
          <pre className="mt-1 ml-2 space-y-1 text-wrap">
            <a href={navigationMatch[1]} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
              {navigationMatch[1]}
            </a>
          </pre>
        </div>
      )}
      {Object.keys(extractedFromPage).length > 0 && (
        <div className="text-sm">
          <Badge variant="outline" className="font-medium">
            Extracted from page
          </Badge>
          <pre className="mt-1 ml-2 space-y-1 text-wrap">{JSON.stringify(extractedFromPage, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export const BrowserUseToolMessage = ({
  args,
  result,
  message,
}: {
  args: any;
  result: { error: string | null; output: string; system: string | null; base64_image: string | null };
  message: AggregatedMessage & { type: 'tool' };
}) => {
  const { currentMessageIndex, setCurrentMessageIndex } = useCurrentMessageIndex();
  const browserMessage = message.messages.find(msg => msg.type === 'agent:browser:browse:complete');
  return (
    <>
      <Popover>
        <PopoverTrigger asChild>
          <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
            <div>
              <span className="font-mono">
                {!result ? '🔍' : result.error ? '🚨' : '🎯'} Browsing{' '}
                <span
                  className="cursor-pointer hover:underline"
                  onClick={e => {
                    e.preventDefault();
                    setCurrentMessageIndex(browserMessage?.index ?? currentMessageIndex);
                  }}
                >
                  {browserMessage?.content.title}
                </span>
              </span>
            </div>
          </Badge>
        </PopoverTrigger>
        <PopoverContent className="w-auto" align="start">
          <BrowserUseToolTooltip args={args} result={result} />
        </PopoverContent>
      </Popover>
      {browserMessage?.content.screenshot && (
        <Badge variant="outline" className="mt-2 cursor-pointer" onClick={() => setCurrentMessageIndex(browserMessage.index ?? currentMessageIndex)}>
          <img
            src={getBase64ImageUrl(browserMessage.content.screenshot)}
            alt={browserMessage.content.title}
            className="mt-2 h-24 w-24 cursor-pointer rounded object-cover object-top"
          />
        </Badge>
      )}
    </>
  );
};
