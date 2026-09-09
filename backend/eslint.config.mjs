// ============================================================
// ESLint flat config — XAU AI PRO backend (Nitro)
// - .mjs / src/**   -> ESM (module)
// - .cjs e .js raiz -> CommonJS (require, module, __dirname)
// ============================================================
import globals from 'globals';

// Auto-imports globales proveidos por Nitro/h3 en runtime (server/api/**)
// https://nitro.build/guide/routing#auto-imports
const nitroGlobals = {
  // h3
  defineEventHandler: 'readonly',
  eventHandler: 'readonly',
  createError: 'readonly',
  readBody: 'readonly',
  readValidatedBody: 'readonly',
  readMultipartFormData: 'readonly',
  getQuery: 'readonly',
  getValidatedQuery: 'readonly',
  getRouterParam: 'readonly',
  getRouterParams: 'readonly',
  getRequestURL: 'readonly',
  getRequestHeaders: 'readonly',
  getRequestHeader: 'readonly',
  setResponseHeader: 'readonly',
  setResponseHeaders: 'readonly',
  setResponseStatus: 'readonly',
  sendRedirect: 'readonly',
  sendError: 'readonly',
  sendNoContent: 'readonly',
  proxyRequest: 'readonly',
  // Nitro
  useRuntimeConfig: 'readonly',
  useStorage: 'readonly',
  useNitroApp: 'readonly',
  useAppConfig: 'readonly',
  useCachedEventHandler: 'readonly',
  defineCachedEventHandler: 'readonly',
  defineCachedFunction: 'readonly',
  cachedEventHandler: 'readonly',
  defineNitroPlugin: 'readonly',
  defineRouteMeta: 'readonly',
  defineTask: 'readonly',
  // ofetch
  $fetch: 'readonly',
};

export default [
  // --- ESM: arquivos .mjs (src/index.mjs) ---
  {
    files: ['src/**/*.mjs', '**/*.mjs'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.node, ...nitroGlobals },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-undef': 'error',
      'no-console': 'off',
      eqeqeq: ['warn', 'smart'],
      'prefer-const': 'warn',
      'no-var': 'error',
    },
  },
  // --- CommonJS: .cjs e .js na raiz ---
  {
    files: ['**/*.cjs', '*.js'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'commonjs',
      globals: { ...globals.node, ...globals.commonjs, ...nitroGlobals },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-undef': 'error',
      'no-console': 'off',
      eqeqeq: ['warn', 'smart'],
      'prefer-const': 'warn',
      'no-var': 'error',
    },
  },
  {
    ignores: [
      'node_modules/**',
      '.output/**',
      '.vercel/**',
      '.nitro/**',
      'dist/**',
    ],
  },
];