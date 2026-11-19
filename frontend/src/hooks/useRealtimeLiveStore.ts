// ===========================================================================
//  ESTADO AO VIVO DA MESA (18/11/2026)
// ===========================================================================
//  "tudo atualizado em tempo real: valores, desenhos, indicadores, calendario,
//  historico, contas, configuracoes" — o pedido do dono.
//
//  POR QUE ESTE HOOK NAO ABRE UM SEGUNDO POLLING
//  =============================================
//  O app ja mantem UMA fonte de verdade para conta, posicoes, ordens e
//  cotacoes: `useAppStore`, alimentado pelo bootstrap do Core e pelo
//  WebSocket de mercado. Criar aqui outro `setInterval` em `/api/mobile/control`
//  daria dois numeros para o mesmo campo — e quando eles divergem, o operador
//  acredita no errado (AGENTS.md §5). Este hook e um ADAPTADOR de leitura:
//  ele nao escreve no gateway, nao busca nada e nao decide preco.
//
//  A UNICA ACAO E `ressincronizar`, que invalida o cache do React Query para
//  que as consultas existentes busquem de novo. Nao inventa contrato novo.
import { useCallback, useEffect, useRef, useState } from 'react';
import { queryClient } from './queries';
import { useAppStore, type Order, type Position } from './useAppStore';

export interface EstadoAoVivo {
  /** WebSocket de mercado conectado NESTE momento. */
  websocket: boolean;
  /** Ha conta lida do gateway (nao presume corretora nem login). */
  temConta: boolean;
  /** Hora local da ultima mudanca observada em qualquer campo ao vivo. */
  ultimaSincronizacao: string;
  saldo: number;
  patrimonio: number;
  flutuante: number;
  margemLivre: number;
  posicoes: Position[];
  ordens: Order[];
  /** Simbolo selecionado pelo operador na barra do app. Vazio e vazio. */
  simbolo: string;
  /** Ultima cotacao do simbolo selecionado, se o Core ja publicou uma. */
  cotacao: { bid: number; ask: number; digits: number; point: number; hora: string } | null;
}

const VAZIO: EstadoAoVivo = {
  websocket: false,
  temConta: false,
  ultimaSincronizacao: '—',
  saldo: 0,
  patrimonio: 0,
  flutuante: 0,
  margemLivre: 0,
  posicoes: [],
  ordens: [],
  simbolo: '',
  cotacao: null,
};

export function useRealtimeLiveStore() {
  const conta = useAppStore((s) => s.account);
  const posicoes = useAppStore((s) => s.positions);
  const ordens = useAppStore((s) => s.orders);
  const cotacoes = useAppStore((s) => s.quotes);
  const websocket = useAppStore((s) => s.wsConnected);
  const simbolo = useAppStore((s) => s.selectedSymbol);

  const [ultima, setUltima] = useState<string>('—');
  const assinatura = useRef<string>('');

  const cotacao = simbolo
    ? cotacoes.find((q) => q.symbol === simbolo) ?? null
    : null;

  useEffect(() => {
    // Assinatura barata do que mudou. Comparar objeto inteiro por JSON a cada
    // tick de preco custaria mais que o proprio render; estes cinco campos
    // cobrem saldo, patrimonio, posicao, ordem e preco.
    const nova = [
      conta?.equity ?? '',
      conta?.balance ?? '',
      posicoes.length,
      ordens.length,
      cotacao?.price ?? '',
      websocket ? '1' : '0',
    ].join('|');
    if (nova === assinatura.current) return;
    assinatura.current = nova;
    setUltima(new Date().toLocaleTimeString('pt-BR'));
  }, [conta?.equity, conta?.balance, posicoes.length, ordens.length, cotacao?.price, websocket]);

  const ressincronizar = useCallback(() => {
    void queryClient.invalidateQueries();
  }, []);

  if (!conta) {
    return { estado: { ...VAZIO, websocket, simbolo, posicoes, ordens, ultimaSincronizacao: ultima }, ressincronizar };
  }

  const estado: EstadoAoVivo = {
    websocket,
    temConta: true,
    ultimaSincronizacao: ultima,
    saldo: Number(conta.balance ?? 0),
    patrimonio: Number(conta.equity ?? 0),
    flutuante: Number(conta.equity ?? 0) - Number(conta.balance ?? 0),
    margemLivre: Number(conta.free_margin ?? 0),
    posicoes,
    ordens,
    simbolo,
    cotacao: cotacao
      ? {
          bid: Number(cotacao.bid ?? 0),
          ask: Number(cotacao.ask ?? 0),
          digits: Number(cotacao.digits ?? 2),
          point: Number(cotacao.point ?? 0),
          hora: String(cotacao.received_at ?? cotacao.timestamp ?? ''),
        }
      : null,
  };

  return { estado, ressincronizar };
}
