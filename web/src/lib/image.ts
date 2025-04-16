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
    const parts = path.split('/');
    if (parts.length >= 3) {
      const newPath = `/workspace/${parts.slice(3).join('/')}`;
      return `/api${newPath}`;
    }
    return `/api${path}`;
  }
  return getBase64ImageUrl(path);
};

export const getFilePath = (path: string | undefined) => {
  if (!path?.includes('/workspace')) return undefined;

  const workspacePath = path.slice(path.indexOf('/workspace'));
  const parts = workspacePath.split('/');

  if (parts.length >= 3) {
    const newPath = `/workspace/${parts.slice(3).join('/')}`;
    return `/api${newPath}`;
  }

  return `/api${workspacePath}`;
};
