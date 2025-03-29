import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getBase64ImageUrl } from '@/lib/image';
import { Message } from '@/types/chat';

export const ChatPreview = ({ message }: { message: Message }) => {
  console.log(message);
  return (
    <Card className="h-full w-full flex flex-col">
      <CardHeader className="flex-none">
        <CardTitle>Manus's Computer</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <Card className="h-full">
          <CardContent className="h-full p-0">
            <div className="w-full h-full overflow-y-auto">
              {message?.type === 'agent:browser:browse:complete' ? (
                <img src={getBase64ImageUrl(message.content.screenshot)} alt="Manus's Computer Screen" className="w-full" />
              ) : (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-pulse text-gray-500">Manus is not using the computer right now...</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </CardContent>
    </Card>
  );
};
