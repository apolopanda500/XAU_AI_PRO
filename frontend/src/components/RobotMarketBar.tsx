// Referencia de mercado dentro da aba Robo.
//
// POR QUE FICOU AQUI E NAO EM UMA ABA SOLTA
// ===========================================
// Operar exige ver o preco no mesmo lugar onde se clica em comprar. Com o
// mercado em outra aba, o operador alternava entre duas telas e a cotacao que
// viu podia ser de outro ativo. Aqui a faixa le o MESMO `selectedSymbol` que o
// painel de execucao usa, entao o preco mostrado e o ativo que sera operado.
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getQuotes,
  normalizeMarketSource,
  type MarketQuote,
  type MarketSource,
} from '../lib/marketApi';
import { escopoAtivo } from '../lib/escopoAtivo';
import { brokerLabel, MARKET_LABELS } from '../lib/brokerCatalog';
import { useAppStore } from '../hooks/useAppStore';
import { formatNumber, formatTime, isMarketStale } from '../lib/marketFormat';
import '../theme/robot-market-bar.css';

const REFRESH_MS = 2_000;

export default function RobotMarketBar() {
  const selectedSymbol = useAppStore((state) => state.selectedSymbol);
  const escopo = escopoAtivo();
  /*
    SEM ESCOPO, SEM FONTE (11/10/2026, decisao do dono: nada de MT5 fixo). Era
    `?? ({ broker: 'mt5', market: 'other' })` — e a faixa nascia falando MT5 e
    cotando por uma corretora que ninguem escolheu. `normalizeMarketSource`
    devolve `null` para fonte desativada/vazia, e agora o `null` atravessa: a
    faixa mostra `sem corretora`, nada e cotado, e o chip diz o motivo.
  */
  const source = useMemo(
    () => normalizeMarketSource(escopo.broker, escopo.market),
    [escopo.broker, escopo.market],
  );
  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [age, setAge] = useState<number | null>(null);
  const [agora, setAgora] = useState(() => Date.now());
  const [erro, setErro] = useState('');

  /*
    NENHUM ATIVO E PRESUMIDO AQUI (09/10/2026)
    ==========================================
    MEDIDO: esta linha era `(selectedSymbol || 'XAUUSD').toUpperCase()`. Com a
    loja sem ativo escolhido, a faixa cotava XAUUSD — um ativo que ninguem
    tinha escolhido, e que pode NAO existir na conta (MEDIDO em
    `volumeUnidade.ts:31`: XAUUSD nao existe no terminal XM). O operador via
    preco de um ativo que nao pediu e que nao pode operar.

    E exatamente a regra do AGENTS.md §3: simbolo vazio e RECUSA COM MOTIVO,
    nunca um ativo padrao. Sem escolha, a faixa mostra `—`, e o chip diz
    `sem ativo` — que e o motivo. O `carregar` ja saia com `if (!simbolo)`,
    entao nenhuma cotacao e pedida: nada de resposta vazia nem de erro.

    O componente inteiro fica LIVRE: ele nao sabe qual ativo existe. Quem sabe
    e a corretora, pelo catalogo. O prompt apenas oferece o que ja la esta.
  */
  const simbolo = String(selectedSymbol ?? '').trim().toUpperCase();

  const carregar = useCallback(
    async (signal: AbortSignal) => {
      if (!simbolo || !source) return;
      const resposta = await getQuotes(source, [simbolo], { signal });
      setQuote(resposta.quotes.find((item) => item.symbol.toUpperCase() === simbolo) ?? null);
      setAge(Date.now());
      setErro('');
    },
    [source, simbolo],
  );

  useEffect(() => {
    const controller = new AbortController();
    setQuote(null);
    setErro('');
    const tick = () => {
      void carregar(controller.signal).catch(() => {
        if (!controller.signal.aborted) setErro('Gateway indisponível');
      });
    };
    void tick();
    const timer = window.setInterval(tick, REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [carregar]);

  // O relogio de staleness roda em 1s: sem isso a faixa marcaria "vencida" com
  // o tempo de espera da proxima leitura e piscaria sem motivo.
  useEffect(() => {
    const timer = window.setInterval(() => setAgora(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  const vencida = age !== null && isMarketStale(age, agora);
  const temPreco = Boolean(
    quote && (quote.bid !== null || quote.ask !== null || quote.last !== null),
  );

  return (
    <section
      className="card compact-card robot-market-bar"
      aria-label="Mercado do ativo selecionado"
    >
      <div className="rmb-top">
        {/*
          O SIMBOLO NAO TROCA AQUI (13/10/2026, menos duplicatas).
          ==========================================================
          Este botao abria um `window.prompt` para trocar o par — o mesmo gesto
          que a barra inferior (StatusBar, com lista e campo) e o seletor da
          operacao automatica ja fazem, os dois gravando no motor. Tres
          controles para o mesmo par e o caminho para discordarem. O prompt,
          alem de duplicado, e bloqueante e some atras da janela.

          A faixa segue mostrando o preco do par; a troca e na barra inferior.
        */}
        <span
          className="rmb-symbol"
          title="Troque o par na barra inferior"
          aria-label={`Ativo operado: ${simbolo || 'nenhum'}`}
        >
          {simbolo || '—'}
        </span>
        <span className="muted">
          {source
            ? `${brokerLabel(source.broker)} · ${MARKET_LABELS[source.market] ?? source.market}`
            : 'sem corretora — ative a conta em Conexões'}
        </span>
          {/*
            O chip separa "sem ativo escolhido" de "sem preco": os dois dizem
            que nao ha numero na tela, mas o motivo e diferente, e o operador
            precisa do motivo para saber ONDE agir — escolher o ativo ou olhar
            a conexao.
          */}
          <span className={`chip ${!simbolo || temPreco ? (!simbolo ? 'warn' : 'ok') : 'warn'}`}>
            {erro ? 'sem gateway' : !simbolo ? 'sem ativo' : !temPreco ? 'sem preço' : vencida ? 'vencida' : 'ao vivo'}
          </span>
        <span className="muted rmb-time">
          {quote?.received_at ? formatTime(quote.received_at) : '--:--:--'}
        </span>
      </div>
      <div className="rmb-quotes">
        <div>
          <em>Último</em>
          <strong className="num">{formatNumber(quote?.last)}</strong>
        </div>
        <div>
          <em>Compra</em>
          <strong className="num">{formatNumber(quote?.bid)}</strong>
        </div>
        <div>
          <em>Venda</em>
          <strong className="num">{formatNumber(quote?.ask)}</strong>
        </div>
        <div>
          <em>Spread</em>
          <strong className="num">{formatNumber(quote?.spread)}</strong>
        </div>
      </div>
    </section>
  );
}
