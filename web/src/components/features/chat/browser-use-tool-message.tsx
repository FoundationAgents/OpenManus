import { Badge } from '@/components/ui/badge';

export const BrowserUseToolMessage = ({ args, completeContent }: { args: any; completeContent?: { result: string } }) => {
  const result = completeContent?.result;

  if (!result) return null;

  const navigationMatch = result.match(/navigated to first result: ([^\s]+)/);
  const urlPattern = /All results:([\s\S]*)/;
  const allResults = result.match(urlPattern)
    ? result
        .match(urlPattern)![1]
        .split('\n')
        .map(url => url.trim())
    : [];
  const extractedFromPageMatch = result.match(/Extracted from page:\n([\s\S]*)/);
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
