/**
 * O sufixo `?raw` é interpretado pelo Vite/Vitest, mas não pelo `tsc`, que vê
 * um caminho de arquivo literal. Esta declaração ensina o TypeScript que
 * qualquer `*.?raw` é um módulo que exporta o código-fonte como string —
 * que é exatamente o que o bundler entrega.
 */
declare module '*?raw' {
  const conteudo: string;
  export default conteudo;
}
