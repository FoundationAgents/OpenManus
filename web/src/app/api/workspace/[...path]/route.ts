import { NextRequest, NextResponse } from 'next/server';
import { verifyToken } from '@/lib/auth';
import path from 'path';
import fs from 'fs';
import sharp from 'sharp';
import { prisma } from '@/lib/prisma';

/**
 * This route is used to serve assets for a task.
 * such like /workspace/[task_id]/[screenshot.png]
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

    const task = await prisma.tasks.findUnique({
      where: { id: path[0] },
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

    const query = request.nextUrl.searchParams;
    const quality = parseInt(query.get('quality') || '80', 10);
    const width = parseInt(query.get('width') || '1080', 10);
    const height = parseInt(query.get('height') || '1080', 10);
    const format = query.get('format') || 'auto';

    const compressedFileBuffer = await compressImage(fileBuffer, { quality, width, height, format });

    return new NextResponse(compressedFileBuffer, {
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

const compressImage = async (
  fileBuffer: Buffer,
  { quality, width, height, format }: { quality: number; width: number; height: number; format: string },
): Promise<Buffer> => {
  try {
    // Get image metadata
    const metadata = await sharp(fileBuffer).metadata();
    const { width: originalWidth, height: originalHeight, format: originalFormat } = metadata;

    if (!originalWidth || !originalHeight) {
      throw new Error('Failed to get image dimensions');
    }

    // Validate input parameters
    if (quality < 1 || quality > 100) {
      throw new Error('Quality must be between 1 and 100');
    }
    if (width < 1 || height < 1) {
      throw new Error('Width and height must be positive numbers');
    }

    // Determine the shorter side
    const maxDimension = Math.min(width, height);
    const isWidthShorter = originalWidth < originalHeight;
    const shorterSide = isWidthShorter ? originalWidth : originalHeight;

    // Calculate scale ratio
    const scale = Math.min(1, maxDimension / shorterSide);
    const targetWidth = Math.round(originalWidth * scale);
    const targetHeight = Math.round(originalHeight * scale);

    // Create sharp instance
    let image = sharp(fileBuffer);

    // Apply resize
    image = image.resize({
      width: targetWidth,
      height: targetHeight,
      fit: 'inside',
      withoutEnlargement: true,
    });

    let targetFormat = format;
    if (format === 'auto') {
      if (originalFormat === 'png' && (await hasTransparency(fileBuffer))) {
        targetFormat = 'png';
      } else if (originalFormat === 'gif') {
        targetFormat = 'gif';
      } else {
        targetFormat = 'webp';
      }
    }

    // Apply format-specific compression
    switch (targetFormat) {
      case 'webp':
        image = image.webp({
          quality,
          effort: 6,
          lossless: false,
        });
        break;
      case 'png':
        image = image.png({
          quality,
          compressionLevel: 9,
          palette: true,
        });
        break;
      case 'jpeg':
      case 'jpg':
        image = image.jpeg({
          quality,
          mozjpeg: true,
          progressive: true,
        });
        break;
      case 'avif':
        image = image.avif({
          quality,
          effort: 6,
          lossless: false,
        });
        break;
      case 'gif':
        break;
      default:
        image = image.webp({
          quality,
          effort: 6,
          lossless: false,
        });
    }

    // Convert to buffer
    return await image.toBuffer();
  } catch (error) {
    console.error('Image compression failed:', error);
    // Return original buffer if compression fails
    return fileBuffer;
  }
};

async function hasTransparency(buffer: Buffer): Promise<boolean> {
  try {
    const metadata = await sharp(buffer).metadata();
    return metadata.hasAlpha === true;
  } catch {
    return false;
  }
}
