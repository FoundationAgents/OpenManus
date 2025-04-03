import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth';
import path from 'path';
import fs from 'fs';
import { prisma } from '@/lib/prisma';

/**
 * This route is used to serve assets for a task.
 * such like /workspace/[organization_id]/[task_id]/[screenshot.png]
 * @param request
 * @param params
 * @returns
 */
export async function GET(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  try {
    const { path } = await params;
    const cookie = request.cookies.get('token');
    if (!cookie) {
      return new NextResponse('Unauthorized', { status: 401 });
    }
    const user = await verifyToken(cookie.value);
    if (!user) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const organizationUser = await prisma.organizationUsers.findFirst({
      where: { userId: user.id },
      select: { organizationId: true },
    });
    if (!organizationUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const organizationId = path[0];
    const taskId = path[1];

    if (organizationId !== organizationUser.organizationId) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const task = await prisma.tasks.findUnique({
      where: { organizationId: organizationId, id: taskId },
      select: { organizationId: true },
    });

    if (!task) {
      return new NextResponse('Task not found', { status: 404 });
    }

    if (task.organizationId !== organizationUser.organizationId) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const filePath = `${process.env.WORKSPACE_ROOT_PATH}/${path.join('/')}`;
    if (!fs.existsSync(filePath)) {
      return new NextResponse('File not found', { status: 404 });
    }

    const fileBuffer = await fs.promises.readFile(filePath);
    const contentType = getContentType(filePath);

    return new NextResponse(fileBuffer, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=31536000',
      },
    });
  } catch (error) {
    console.error('Error serving protected asset:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}

function getContentType(filePath: string): string {
  const ext = path.extname(filePath).toLowerCase();
  const contentTypes: Record<string, string> = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.md': 'text/markdown',
  };
  return contentTypes[ext] || 'application/octet-stream';
}
