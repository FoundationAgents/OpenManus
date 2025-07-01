/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NEED_INVITE_CODE: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_JWT_SECRET: string;
  // 更多环境变量...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
