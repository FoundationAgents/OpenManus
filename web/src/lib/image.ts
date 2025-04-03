import querystring from 'querystring';

export const getBase64ImageUrl = (base64String: string) => {
  if (!base64String) return '';
  if (base64String.startsWith('data:image')) {
    return base64String;
  }
  return `data:image/png;base64,${base64String}`;
};

export const getImageUrl = (path: string) => {
  if (path.startsWith('/workspace')) {
    return `/api${path}`;
  }
  return getBase64ImageUrl(path);
};

export const getFilePath = (path: string | undefined) => {
  return path?.includes('/workspace') ? `/api${path.slice(path.indexOf('/workspace'))}` : undefined;
};
