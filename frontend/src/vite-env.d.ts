/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NEED_INVITE_CODE: string;
  readonly VITE_API_BASE_URL: string;
  readonly VITE_JWT_SECRET: string;
  // More environment variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
