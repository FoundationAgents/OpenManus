import { useCurrentMessageIndex } from '@/app/tasks/hooks';
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { getImageUrl } from '@/lib/image';
import { AggregatedMessage } from '@/types/chat';

export const BrowserUseToolTooltip = ({
  args,
  result,
}: {
  args: any;
  result: {
    error: string | null;
    output?: string;
    system: string | null;
    base64_image: string | null;
  };
}) => {
  if (!result) return null;

  const navigationMatch = result.output?.match(/navigated to first result: ([^\s]+)/);
  const urlPattern = /All results:([\s\S]*)/;
  const allResults = result.output?.match(urlPattern)
    ? result.output
        .match(urlPattern)![1]
        .split('\n')
        .map(url => url.trim())
    : [];
  const extractedFromPageMatch = result.output?.match(/Extracted from page:\n([\s\S]*)/);
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

  const action = args.action;

  const renderAction = (action: string) => {
    if (action === 'go_to_url') {
      // if agent:tool:execute:complete exist, but no browserMessage, then it means the agent is failed
      const failed = message.messages.find(msg => msg.type === 'agent:tool:execute:complete') && !browserMessage;
      return (
        <>
          {failed ? 'Failed to navigate to' : 'Browsing '}
          <span
            className="cursor-pointer hover:underline"
            onClick={e => {
              e.preventDefault();
              if (browserMessage?.content.title) {
                setCurrentMessageIndex(browserMessage?.index ?? currentMessageIndex);
              } else {
                window.open(args.url, '_blank');
              }
            }}
          >
            {browserMessage?.content.title || args.url}
          </span>
        </>
      );
    }
    if (action === 'web_search') {
      return `Searching for ${args.query}`;
    }
    if (action === 'extract_content') {
      return 'Extracting content';
    }
    if (action === 'scroll_down') {
      return `Scroll down ${args.scroll_amount}px`;
    }
    if (action === 'scroll_up') {
      return `Scroll up ${args.scroll_amount}px`;
    }
    if (action === 'scroll_to_text') {
      return `Scroll to text: ${args.text}`;
    }
    if (action === 'click_element') {
      return `Click element Index: ${args.index}`;
    }
    if (action === 'input_text') {
      return `Input text: ${args.text}`;
    }
    if (action === 'send_keys') {
      return `Send keys: ${args.keys}`;
    }
    if (action === 'get_dropdown_options') {
      return `Get dropdown options`;
    }
    if (action === 'refresh') {
      return 'Refresh';
    }
  };

  const isShowScreenshot = browserMessage?.content.screenshot && (action === 'go_to_url' || action === 'web_search');

  return (
    <>
      <Popover>
        <PopoverTrigger asChild>
          <Badge variant="outline" className="flex cursor-pointer items-center gap-2">
            <div>
              <span className="font-mono">
                {!result ? '🔍' : result.error ? '🚨' : '🎯'} {renderAction(action)}
              </span>
            </div>
          </Badge>
        </PopoverTrigger>
        <PopoverContent className="w-auto" align="start">
          <BrowserUseToolTooltip args={args} result={result} />
        </PopoverContent>
      </Popover>
      {isShowScreenshot && (
        <Badge variant="outline" className="mt-2 cursor-pointer" onClick={() => setCurrentMessageIndex(browserMessage.index ?? currentMessageIndex)}>
          <img
            src={getImageUrl(browserMessage.content.screenshot, { quality: 80, width: 100, height: 100 })}
            alt={browserMessage.content.title}
            className="my-1 h-24 w-24 cursor-pointer rounded object-cover object-top"
            onError={e => {
              e.currentTarget.style.display = 'none';
              const parentNode = e.currentTarget.parentNode;
              const existingIcon = parentNode?.querySelector('.image-fallback-icon');
              if (!existingIcon) {
                const iconContainer = document.createElement('div');
                iconContainer.className = 'my-1 h-24 w-24 flex items-center justify-center rounded bg-muted image-fallback-icon';
                iconContainer.innerHTML =
                  '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-image"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>';
                parentNode?.appendChild(iconContainer);
              }
            }}
          />
        </Badge>
      )}
      {action === 'extract_content' && <div className="mt-2 rounded-lg p-2 text-xs">{args.goal}</div>}
    </>
  );
};
