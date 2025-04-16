import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth';
import fs from 'fs';
import { prisma } from '@/lib/prisma';
import archiver from 'archiver';

/**
 * This route is used to download workspace files or directories as zip archives
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

    const taskId = path[0];

    const task = await prisma.tasks.findUnique({
      where: { id: taskId, organizationId: organizationUser.organizationId },
    });

    if (!task) {
      return new NextResponse('Task not found', { status: 404 });
    }

    const filePath = `${process.env.WORKSPACE_ROOT_PATH}/${organizationUser.organizationId}/${path.join('/')}`;
    if (!fs.existsSync(filePath)) {
      return new NextResponse('File not found', { status: 404 });
    }

    const stats = fs.statSync(filePath);

    // If it's a single file, simply return it for download
    if (!stats.isDirectory()) {
      const fileBuffer = await fs.promises.readFile(filePath);
      const fileName = filePath.split('/').pop() || 'download';

      return new NextResponse(fileBuffer, {
        headers: {
          'Content-Type': 'application/octet-stream',
          'Content-Disposition': `attachment; filename="${fileName}"`,
        },
      });
    }

    // For directories, create a zip archive
    const directoryName = filePath.split('/').pop() || 'workspace';
    const zipFileName = `${directoryName}.zip`;

    // Create zip archive in memory
    const archive = archiver('zip', {
      zlib: { level: 9 }, // Compression level
    });

    // Collect the chunks of the zip file
    const chunks: Buffer[] = [];

    archive.on('data', (chunk: any) => {
      chunks.push(Buffer.from(chunk));
    });

    // Handle archive warnings
    archive.on('warning', (err: any) => {
      if (err.code === 'ENOENT') {
        console.warn('Archive warning:', err);
      } else {
        console.error('Archive error:', err);
      }
    });

    // Handle archive errors
    archive.on('error', (err: any) => {
      console.error('Archive error:', err);
    });

    // Function to recursively add files to the zip
    const addFilesToArchive = (currentPath: string, relativePath = '') => {
      const items = fs.readdirSync(currentPath);

      for (const item of items) {
        const itemPath = `${currentPath}/${item}`;
        const itemRelativePath = relativePath ? `${relativePath}/${item}` : item;
        const itemStat = fs.statSync(itemPath);

        if (itemStat.isDirectory()) {
          // Recursively add directory contents
          addFilesToArchive(itemPath, itemRelativePath);
        } else {
          // Add file to archive
          archive.file(itemPath, { name: itemRelativePath });
        }
      }
    };

    // Add files to the archive
    addFilesToArchive(filePath);

    // Finalize the archive
    await archive.finalize();

    // Combine all chunks into a single buffer
    const zipBuffer = Buffer.concat(chunks);

    // Return the zip file
    return new NextResponse(zipBuffer, {
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="${zipFileName}"`,
      },
    });
  } catch (error) {
    console.error('Error creating download:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
