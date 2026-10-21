import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    globals: false,
    /*
      O duble de ambiente do grafico (06/10/2026).
      ==================================================
      `lightweight-charts` chama `window.matchMedia` e `ResizeObserver` ao
      criar o canvas, e o jsdom nao tem nenhum dos dois. Sem este `setupFiles`,
      o primeiro teste que RENDERIZA o `PriceChart` morre com
      `TypeError: matchMedia is not a function` — um erro de ambiente que
      reprova antes de o componente rodar.

      Ate entao so os testes das FUNCOES PURAS do grafico existiam
      (`emaValores`, `rsiValores`, `macdValores`), e eles nao tocam no canvas —
      por isso a lacuna nunca apareceu. Ver `src/test/setupAmbienteGrafico.ts`.
    */
    setupFiles: ['./src/test/setupAmbienteGrafico.ts'],
  },
});