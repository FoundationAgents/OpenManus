import { Badge } from '@/components/ui/badge';
import { AggregatedMessage } from '@/types/chat';

export const BrowserUseToolMessage = ({ message }: { message: AggregatedMessage }) => {
  if (message.type !== 'tool') return null;

  const argsMessage = message.messages.find(msg => msg.type === 'tool:arguments');

  const { action, ...params } = JSON.parse(argsMessage?.content.match(/\{.*\}/)?.[0] || '{}');

  const completedMessage = message.messages.find(msg => msg.type === 'tool:completed');
  const result = completedMessage?.content;

  if (!result) return null;
  const commandMatch = result.match(/Tool '([^']+)' completed its mission! Result: Observed output of cmd `([^`]+)` executed/);
  if (!commandMatch) return result;

  const content = result.replace(commandMatch[0], '').trim();

  const navigationMatch = content.match(/navigated to first result: ([^\s]+)/);

  const urlPattern = /All results:([\s\S]*)/;
  const allResults = content.match(urlPattern)
    ? content
        .match(urlPattern)![1]
        .split('\n')
        .map(url => url.trim())
    : [];

  // Extracted from page:
  const extractedFromPageMatch = content.match(/Extracted from page:\n([\s\S]*)/);
  console.log('Extracted from page:', extractedFromPageMatch);
  const extractedFromPage = extractedFromPageMatch ? JSON.parse(extractedFromPageMatch[1]) : {};

  console.log('Content:', content);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 text-wrap">
        {Object.entries(params).map(([key, value]) => (
          <div key={key} className="text-sm">
            <Badge variant="outline" className="font-medium cursor-pointer">
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
              <a key={index} href={url} target="_blank" rel="noopener noreferrer" className="block text-blue-500 hover:underline truncate">
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
