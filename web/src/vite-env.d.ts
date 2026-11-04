/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Set to "true" at build time to surface the seeded demo logins on the sign-in page. */
  readonly VITE_DEMO_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
