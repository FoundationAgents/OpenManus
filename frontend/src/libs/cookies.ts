// 简单的cookies工具，用于客户端获取cookie
export function getCookie(name: string): string | undefined {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop()?.split(';').shift();
  }
  return undefined;
}

export function setCookie(
  name: string,
  value: string,
  options?: {
    expires?: Date;
    path?: string;
    domain?: string;
    secure?: boolean;
    sameSite?: 'strict' | 'lax' | 'none';
  },
) {
  let cookie = `${name}=${value}`;

  if (options?.expires) {
    cookie += `; expires=${options.expires.toUTCString()}`;
  }
  if (options?.path) {
    cookie += `; path=${options.path}`;
  }
  if (options?.domain) {
    cookie += `; domain=${options.domain}`;
  }
  if (options?.secure) {
    cookie += '; secure';
  }
  if (options?.sameSite) {
    cookie += `; samesite=${options.sameSite}`;
  }

  document.cookie = cookie;
}

export function deleteCookie(
  name: string,
  options?: {
    path?: string;
    domain?: string;
  },
) {
  setCookie(name, '', {
    ...options,
    expires: new Date(0),
  });
}
