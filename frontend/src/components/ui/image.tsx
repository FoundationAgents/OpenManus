import { forwardRef } from 'react';
import type { ImgHTMLAttributes } from 'react';

export interface ImageProps extends ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  width?: number;
  height?: number;
  priority?: boolean;
  className?: string;
}

export const Image = forwardRef<HTMLImageElement, ImageProps>(({ src, alt, width, height, priority, className, ...props }, ref) => {
  return <img ref={ref} src={src} alt={alt} width={width} height={height} className={className} loading={priority ? 'eager' : 'lazy'} {...props} />;
});

Image.displayName = 'Image';
