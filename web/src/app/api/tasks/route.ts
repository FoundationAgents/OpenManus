import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = 'http://localhost:5172';

export async function POST(request: NextRequest) {
  const { prompt } = await request.json();
  const response = await fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    return NextResponse.json({ error: 'Failed to create task' }, { status: 500 });
  }

  return NextResponse.json(await response.json());
}
