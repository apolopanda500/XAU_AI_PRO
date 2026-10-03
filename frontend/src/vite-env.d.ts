/**
 * Tipagens do ambiente Vite: `import.meta.glob`, `import.meta.env` e o
 * sufixo `?raw`.
 *
 * O `?raw` é interpretado pelo Vite/Vitest, mas não pelo `tsc`, que vê um
 * caminho de arquivo literal. A declaração de `*?raw` vem do próprio
 * `vite/client`, que também ensina o TypeScript o glob de import — usado
 * pelos testes que leem o código-fonte dos componentes como string.
 */
/// <reference types="vite/client" />
