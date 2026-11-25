// @vitest-environment jsdom
// PROVA NEGATIVA DO LOOP DE WS (25/11/2026, APK em forward real).
//
// O gateway FastAPI declara `transport: http-polling, websocket: false`: nao
// existe `/ws/market`. O hook abria WebSocket de qualquer forma, o socket
// fechava, `onclose` chamava `connectWebSocket()` de novo e o backoff mantinha
// o WebView em redesenho continuo (`could not get idle state` no uiautomator).
// `temWsConfigurado()` existia em `lib/api.ts` e nao tinha consumidor nenhum
// — controle sem leitor e, por isso, um defeito (AGENTS.md 9).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

const H = vi.hoisted(() => ({
  configurado: false,
  construtores: 0,
}));

vi.mock('../lib/api', async (importOriginal) => {
  const real = await importOriginal<typeof import('../lib/api')>();
  return { ...real, temWsConfigurado: () => H.configurado };
});

class WebSocketFalso {
  static readonly OPEN = 1;
  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: (() => void) | null = null;

  constructor(_url: string) {
    H.construtores += 1;
  }

  send(): void {}
  close(): void {}
}

const { useMarketWebSocket } = await import('./useMarketWebSocket');

function Harness() {
  useMarketWebSocket();
  return null;
}

describe('useMarketWebSocket — nenhum socket contra gateway sem WebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    H.configurado = false;
    H.construtores = 0;
    vi.stubGlobal('WebSocket', WebSocketFalso);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('sem WS configurado, NAO chama new WebSocket nem apos varias reconexoes', () => {
    render(<Harness />);
    // 60s cobre toda a escada de backoff (1s, 2s, 4s, 8s, 16s, 30s).
    vi.advanceTimersByTime(60_000);
    expect(H.construtores).toBe(0);
  });

  it('PROVA NEGATIVA: com WS configurado, o caminho real continua abrindo o socket', () => {
    H.configurado = true;
    render(<Harness />);
    vi.advanceTimersByTime(1_100);
    expect(H.construtores).toBe(1);
  });
});
