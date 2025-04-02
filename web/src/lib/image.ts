import querystring from 'querystring';

export const getBase64ImageUrl = (base64String: string) => {
  if (!base64String) return '';
  if (base64String.startsWith('data:image')) {
    return base64String;
  }
  return `data:image/png;base64,${base64String}`;
};

export const getImageUrl = (path: string, params?: { quality?: number; width?: number; height?: number }) => {
  if (path.startsWith('/workspace')) {
    return `/api${path}?${querystring.stringify(params)}`;
  }
  return getBase64ImageUrl(path);
};
