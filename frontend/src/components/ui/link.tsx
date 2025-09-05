import { Link as RouterLink, type LinkProps as RouterLinkProps } from 'react-router-dom';
import { forwardRef } from 'react';

export interface LinkProps extends Omit<RouterLinkProps, 'to'> {
  href: string;
  children: React.ReactNode;
}

export const Link = forwardRef<HTMLAnchorElement, LinkProps>(({ href, children, ...props }, ref) => {
  return (
    <RouterLink ref={ref} to={href} {...props}>
      {children}
    </RouterLink>
  );
});

Link.displayName = 'Link';
