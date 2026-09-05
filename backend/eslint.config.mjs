// ============================================================
// ESLint flat config — XAU AI PRO backend (Nitro)
// - .mjs / src/**   -> ESM (module)
// - .cjs e .js raiz -> CommonJS (require, module, __dirname)
// ============================================================
import globals from 'globals';

export default [
  // --- ESM: arquivos .mjs (src/index.mjs) ---
  {
    files: ['src/**/*.mjs', '**/*.mjs'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.node },
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
      globals: { ...globals.node, ...globals.commonjs },
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