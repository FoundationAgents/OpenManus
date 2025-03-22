import { NextRequest } from 'next/server';

const API_BASE_URL = 'http://localhost:5172';

export async function GET(_request: NextRequest, { params }: { params: Promise<{ task_id: string }> }) {
  try {
    const taskId = (await params).task_id;
    const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/events`);

    if (!response.ok) {
      throw new Error(`Failed to fetch task events: ${response.statusText}`);
    }

    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Failed to get response stream');
    }

    (async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          await writer.write(value);
        }
        await writer.close();
      } catch (error) {
        console.error('Error processing stream:', error);
        await writer.abort(error);
      } finally {
        reader.releaseLock();
      }
    })();

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Error processing task events:', error);
    return new Response(JSON.stringify({ error: 'Failed to process task events' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
