/**
 * Sincronizacao da sessao MT5 em TODOS os mercados de uma vez.
 *
 * POR QUE ESTE MODULO EXISTE (25/11/2026)
 * =======================================
 * MEDIDO no APK 1.2.191: `Sincronizar MT5` registrava uma unica conexao —
 * `marketsFor('mt5')[0]` — porque `MT5AccountsPanel` e `ConnectionSettings`
 * cada um chamava `saveExchange` com um mercado so. O operador via uma linha
 * (forex) e acreditava que o terminal servia so um mercado, embora o backend
 * já aceite os nove (`backend/broker_registry.py`) e `connection_store.py`
 * trate sessao MT5 como valida para qualquer mercado da corretora.
 *
 * Aqui o catalogo e percorrido UMA vez, no mesmo caminho das outras conexoes:
 * `detectTerminal()` (leitura), `saveExchange()` (gravacao sem segredo) e
 * `connectionAction(id, 'test')` (leitura). Nenhuma ordem e enviada.
 *
 * O QUE NAO MUDA
 * ==============
 * O escopo ATIVO continua sendo um unico par `broker:market` + ID (`escopoAtivo`),
 * porque o motor resolve a conta por ID. Registrar os nove mercados nao liga
 * nove contas para operar: da ao operador nove linhas legiveis e uma escolha.
 * Quem decide qual fica ativo e o chamador, nao este modulo.
 */
import {
  connectionAction,
  detectTerminal,
  marketsFor,
  saveExchange,
  type TerminalAccount,
} from './connections';

export type FalhaMercadoMt5 = { market: string; motivo: string };

export type RelatorioSincronizacaoMt5 = {
  conta: TerminalAccount;
  rotulo: string;
  mercados: readonly string[];
  /** market -> ID gravado, para o chamador escolher o escopo ativo. */
  ids: Record<string, string>;
  registradas: string[];
  validadas: string[];
  falhas: FalhaMercadoMt5[];
};

/**
 * O rotulo da linha. Vem da sessao lida, nunca de um nome inventado.
 * O nome digitado pelo operador manda; o servidor digitado so entra no fallback.
 */
export function rotuloDaContaMt5(
  conta: TerminalAccount,
  nomeDigitado = '',
  servidorDigitado = '',
): string {
  const servidor = servidorDigitado.trim() || String(conta.server || '').trim();
  return (
    nomeDigitado.trim() ||
    [conta.name, servidor].filter(Boolean).join(' @ ') ||
    `conta ${conta.login}`
  );
}

/**
 * Le a sessao e registra/testa todos os mercados do catalogo MT5.
 *
 * Uma falha em um mercado NAO apaga o trabalho dos outros: o relatorio traz
 * `falhas` com mercado e motivo. Se nenhum mercado foi registrado, lanca —
 * o chamador nao pode dizer "sincronizado" quando nada foi gravado.
 */
export async function sincronizarMercadosMt5(
  opcoes: { nome?: string; servidor?: string; mercados?: readonly string[] } = {},
): Promise<RelatorioSincronizacaoMt5> {
  const conta = await detectTerminal();
  const catalogo = marketsFor('mt5');
  const mercados = (opcoes.mercados ?? catalogo).filter((item) => catalogo.includes(item));
  if (!mercados.length) {
    throw new Error('O catalogo MT5 nao informou mercados para sincronizar.');
  }

  const rotulo = rotuloDaContaMt5(conta, opcoes.nome, opcoes.servidor);
  const relatorio: RelatorioSincronizacaoMt5 = {
    conta,
    rotulo,
    mercados: [...mercados],
    ids: {},
    registradas: [],
    validadas: [],
    falhas: [],
  };

  for (const market of mercados) {
    try {
      const id = await saveExchange('mt5', market, rotulo, '', '');
      relatorio.ids[market] = id;
      relatorio.registradas.push(id);
      // `test` e leitura da conta. Nao e `activate`, nem ordem.
      await connectionAction(id, 'test');
      relatorio.validadas.push(id);
    } catch (exc) {
      relatorio.falhas.push({
        market,
        motivo: exc instanceof Error ? exc.message : String(exc),
      });
    }
  }

  if (!relatorio.registradas.length) {
    const motivos = relatorio.falhas.map((falha) => `${falha.market}: ${falha.motivo}`).join('; ');
    throw new Error(`Nenhum mercado MT5 foi registrado. ${motivos}`.trim());
  }
  return relatorio;
}

/** Texto curto para a tela: o que foi registrado, o que falhou, sem ordens. */
export function resumoSincronizacaoMt5(relatorio: RelatorioSincronizacaoMt5): string {
  const total = relatorio.mercados.length;
  const registradas = relatorio.registradas.length;
  const validadas = relatorio.validadas.length;
  const lista = relatorio.mercados.join(', ');
  const partes = [
    `Conta ${relatorio.conta.login} @ ${relatorio.conta.server}:`,
    `${registradas}/${total} mercados registrados (${lista})`,
    `${validadas}/${total} leituras validadas`,
  ];
  if (relatorio.falhas.length) {
    partes.push(
      `falhas: ${relatorio.falhas.map((falha) => `${falha.market} (${falha.motivo})`).join('; ')}`,
    );
  }
  partes.push('Nenhuma ordem foi enviada.');
  return partes.join(' · ');
}

/** Mercado de um ID devolvido pelo relatorio, para gravar o escopo ativo. */
export function mercadoDoIdMt5(
  relatorio: RelatorioSincronizacaoMt5,
  id: string,
): string | undefined {
  return Object.keys(relatorio.ids).find((market) => relatorio.ids[market] === id);
}
