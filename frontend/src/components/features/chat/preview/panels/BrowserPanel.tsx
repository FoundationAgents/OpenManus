import { getImageUrl } from '@/libs/image';

interface BrowserPanelProps {
  url?: string;
  title?: string;
  screenshot?: string;
}

export const BrowserPanel = ({ url, title, screenshot }: BrowserPanelProps) => (
  <div className="flex h-full flex-col overflow-hidden rounded-md border bg-black">
    {/* macOS-style chrome bar */}
    <div className="flex min-h-10 items-center gap-2 border-b bg-background px-3 py-2">
      <div className="flex gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
      </div>
      <div className="bg-muted text-muted-foreground min-w-0 flex-1 rounded px-2 py-1 text-xs">
        <div className="truncate">{url || title || 'Browser preview'}</div>
      </div>
    </div>
    <div className="min-h-0 flex-1 overflow-auto bg-neutral-950">
      {screenshot ? (
        <img
          src={getImageUrl(screenshot)}
          alt="Browser screenshot"
          className="mx-auto h-auto w-full"
        />
      ) : (
        <div className="flex h-full items-center justify-center text-xs text-neutral-500">
          No screenshot available
        </div>
      )}
    </div>
  </div>
);
