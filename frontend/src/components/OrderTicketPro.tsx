// ===========================================================================
//  BOLETA PROFISSIONAL — CALCULADORA COM TRAVA DE RISCO (18/11/2026)
// ===========================================================================
//  "criar ordens, operar tudo 10/10" — mas a REGRA do projeto continua: nao
//  existe execucao real sem autorizacao explicita do dono, sem `request_id`
//  idempotente, sem `confirm=true` e sem o RiskGate do gateway
//  (AGENTS.md §4). Esta boleta NAO inventa um endpoint de ordem: o frontend
//  nao tem hoje nenhum contrato de envio, e criar um aqui seria o §5 na
//  pratica — dois lados do mesmo dado com nomes diferentes.
//
//  O QUE ELA FAZ
//  =============
//  * calcula niveis de SL/TP a partir da cotacao REAL do Core;
//  * calcula o risco em dinheiro com `valorDoNivel` de `lib/risco.ts` — a
//    MESMA funcao que a tela de operacao ja usa. Sem `contract_size` da
//    corretora o risco aparece como "depende do contrato", nunca como numero
//    inventado;
//  * recusa nos mesmos casos em que o RiskGate recusaria: simbolo vazio,
//    Stop Loss zerado, risco acima do limite e modo somente leitura;
//  * com `onSolicitarOrdem` o dono pluga o executor autorizado; sem ele, o
//    botao diz "SEM ENVIO" e nada sai do aparelho.
//
//  NENHUM SIMBOLO E PRESUMIDO. Sem `symbol`, a boleta mostra a recusa com
//  motivo — e a trava `ativoPresumido.test.ts` continua valendo.
import { useMemo, useState } from 'react';
import { SEM_CONTRATO, valorDoNivel, type Ficha } from '../lib/risco';

export type TipoOrdem = 'MERCADO' | 'LIMITE_COMPRA' | 'LIMITE_VENDA' | 'STOP_COMPRA' | 'STOP_VENDA';
export type LadoOrdem = 'COMPRA' | 'VENDA';

export interface OrdemSolicitada {
  symbol: string;
  tipo: TipoOrdem;
  lado: LadoOrdem;
  volume: number;
  preco: number;
  sl: number;
  tp: number;
  pontosSL: number;
  pontosTP: number;
  riscoEstimado: number | null;
}

export interface OrderTicketProProps {
  /** Simbolo escolhido pelo operador. Vazio = recusa com motivo. */
  symbol: string;
  bid: number;
  ask: number;
  digits: number;
  point: number;
  /** Ficha da corretora: `contractSize` e o que converte lote em dinheiro. */
  ficha?: Ficha;
  balance: number;
  /** Limite de risco por ordem em % do saldo, se o gateway informar. */
  limiteRiscoPct?: number;
  /** Verdadeiro quando o gateway declara `read_only`. */
  somenteLeitura: boolean;
  /** Ausente = calculadora; presente = caminho para o executor autorizado. */
  onSolicitarOrdem?: (ordem: OrdemSolicitada) => void;
}

const arredondar = (v: number, digits: number) => {
  const f = 10 ** Math.max(0, Math.min(8, digits));
  return Math.round(v * f) / f;
};

const dinheiro = (v: number) =>
  `$${v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function OrderTicketPro({
  symbol,
  bid,
  ask,
  digits,
  point,
  ficha,
  balance,
  limiteRiscoPct,
  somenteLeitura,
  onSolicitarOrdem,
}: OrderTicketProProps) {
  const [tipo, setTipo] = useState<TipoOrdem>('MERCADO');
  const [lado, setLado] = useState<LadoOrdem>('COMPRA');
  const [volume, setVolume] = useState<number>(0.01);
  const [precoGatilho, setPrecoGatilho] = useState<number>(0);
  const [pontosSL, setPontosSL] = useState<number>(0);
  const [pontosTP, setPontosTP] = useState<number>(0);
  const [confirmado, setConfirmado] = useState<boolean>(false);

  const simboloAusente = !symbol.trim();
  const cotacaoAusente = !(ask > 0 || bid > 0);
  const precoMercado = lado === 'COMPRA' ? ask : bid;
  const entrada = tipo === 'MERCADO' ? precoMercado : precoGatilho;

  const calculo = useMemo(() => {
    const p = Number(point) > 0 ? Number(point) : 0;
    if (!Number.isFinite(entrada) || entrada <= 0 || p <= 0) {
      return { sl: 0, tp: 0, risco: null as number | null, rr: null as number | null };
    }
    const sinal = lado === 'COMPRA' ? -1 : 1;
    const sl = pontosSL > 0 ? arredondar(entrada + sinal * pontosSL * p, digits) : 0;
    const tp = pontosTP > 0 ? arredondar(entrada - sinal * pontosTP * p, digits) : 0;
    const risco = sl > 0 ? valorDoNivel(entrada, sl, volume, ficha) : null;
    const rr = pontosSL > 0 && pontosTP > 0 ? pontosTP / pontosSL : null;
    return { sl, tp, risco, rr };
  }, [entrada, lado, pontosSL, pontosTP, point, digits, volume, ficha]);

  const riscoPct =
    calculo.risco !== null && balance > 0 ? (calculo.risco / balance) * 100 : null;
  const acimaDoLimite =
    riscoPct !== null && typeof limiteRiscoPct === 'number' && riscoPct > limiteRiscoPct;

  const bloqueios: string[] = [];
  if (simboloAusente) bloqueios.push('Sem simbolo: escolha o ativo no catalogo da corretora.');
  if (cotacaoAusente) bloqueios.push('Sem cotacao do Core para este ativo.');
  if (!(pontosSL > 0)) bloqueios.push('Stop Loss obrigatorio: ordem sem SL e recusada pelo RiskGate.');
  if (acimaDoLimite)
    bloqueios.push(
      `Risco de ${(riscoPct as number).toFixed(2)}% acima do limite de ${Number(limiteRiscoPct).toFixed(2)}%.`,
    );
  if (somenteLeitura) bloqueios.push('Gateway em modo SOMENTE LEITURA: o envio esta desligado.');
  if (!onSolicitarOrdem) bloqueios.push('Execucao nao autorizada nesta build: a boleta apenas calcula.');

  const podeEnviar = bloqueios.length === 0 && confirmado;
  const rotuloBotao = !onSolicitarOrdem
    ? 'CALCULADORA — SEM ENVIO'
    : somenteLeitura
      ? 'SOMENTE LEITURA'
      : `ENVIAR ${lado} ${volume.toFixed(2)} ${symbol || '—'}`;

  return (
    <div className="boleta">
      <header className="boleta-topo">
        <div>
          <span className="boleta-titulo">
            BOLETA · {simboloAusente ? 'SEM ATIVO' : symbol}
          </span>
          <div className="boleta-cotacao">
            Bid <strong className="kpi-negativo">{bid > 0 ? bid.toFixed(digits) : '—'}</strong> · Ask{' '}
            <strong className="kpi-positivo">{ask > 0 ? ask.toFixed(digits) : '—'}</strong>
          </div>
        </div>
        <span className={`boleta-selo ${somenteLeitura ? 'boleta-selo-leitura' : 'boleta-selo-armado'}`}>
          {somenteLeitura ? 'SOMENTE LEITURA' : 'RISK GATE ATIVO'}
        </span>
      </header>

      <div className="boleta-tipos" role="group" aria-label="Tipo de ordem">
        {(
          [
            ['MERCADO', 'A mercado'],
            ['LIMITE_COMPRA', 'Buy limit'],
            ['LIMITE_VENDA', 'Sell limit'],
            ['STOP_COMPRA', 'Buy stop'],
            ['STOP_VENDA', 'Sell stop'],
          ] as Array<[TipoOrdem, string]>
        ).map(([id, rotulo]) => (
          <button
            key={id}
            type="button"
            className={`boleta-tipo ${tipo === id ? 'ativo' : ''}`}
            aria-pressed={tipo === id}
            onClick={() => {
              setTipo(id);
              if (id.endsWith('COMPRA')) setLado('COMPRA');
              if (id.endsWith('VENDA')) setLado('VENDA');
            }}
          >
            {rotulo}
          </button>
        ))}
      </div>

      <div className="boleta-lados">
        <button
          type="button"
          className={`boleta-lado boleta-lado-compra ${lado === 'COMPRA' ? 'ativo' : ''}`}
          aria-pressed={lado === 'COMPRA'}
          onClick={() => setLado('COMPRA')}
        >
          COMPRA {ask > 0 ? ask.toFixed(digits) : ''}
        </button>
        <button
          type="button"
          className={`boleta-lado boleta-lado-venda ${lado === 'VENDA' ? 'ativo' : ''}`}
          aria-pressed={lado === 'VENDA'}
          onClick={() => setLado('VENDA')}
        >
          VENDA {bid > 0 ? bid.toFixed(digits) : ''}
        </button>
      </div>

      <div className="boleta-campos">
        <label>
          Volume (lotes)
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(Math.max(0.01, Number(e.target.value) || 0.01))}
          />
        </label>
        {tipo !== 'MERCADO' && (
          <label>
            Preco gatilho
            <input
              type="number"
              step={point > 0 ? point : 0.01}
              value={precoGatilho || ''}
              onChange={(e) => setPrecoGatilho(Number(e.target.value) || 0)}
            />
          </label>
        )}
        <label>
          Stop Loss (pontos)
          <input
            type="number"
            min="0"
            step="10"
            value={pontosSL || ''}
            onChange={(e) => setPontosSL(Math.max(0, Math.trunc(Number(e.target.value) || 0)))}
          />
        </label>
        <label>
          Take Profit (pontos)
          <input
            type="number"
            min="0"
            step="10"
            value={pontosTP || ''}
            onChange={(e) => setPontosTP(Math.max(0, Math.trunc(Number(e.target.value) || 0)))}
          />
        </label>
      </div>

      <dl className="boleta-resumo">
        <div>
          <dt>Entrada</dt>
          <dd>{entrada > 0 ? entrada.toFixed(digits) : '—'}</dd>
        </div>
        <div>
          <dt>SL</dt>
          <dd>{calculo.sl > 0 ? calculo.sl.toFixed(digits) : '—'}</dd>
        </div>
        <div>
          <dt>TP</dt>
          <dd>{calculo.tp > 0 ? calculo.tp.toFixed(digits) : '—'}</dd>
        </div>
        <div>
          <dt>Risco</dt>
          <dd className={acimaDoLimite ? 'kpi-negativo' : ''}>
            {calculo.risco === null
              ? SEM_CONTRATO
              : `${dinheiro(calculo.risco)}${riscoPct === null ? '' : ` (${riscoPct.toFixed(2)}%)`}`}
          </dd>
        </div>
        <div>
          <dt>R:R</dt>
          <dd>{calculo.rr === null ? '—' : `1:${calculo.rr.toFixed(2)}`}</dd>
        </div>
      </dl>

      {calculo.risco === null && !simboloAusente && !cotacaoAusente ? (
        <p className="boleta-aviso">
          A corretora nao informou o tamanho do contrato para este ativo. Sem ele o risco em
          dinheiro nao existe — e inventar um seria pior que nao mostrar.
        </p>
      ) : null}

      <ul className="boleta-bloqueios">
        {bloqueios.map((b) => (
          <li key={b}>{b}</li>
        ))}
      </ul>

      <label className="boleta-confirmar">
        <input
          type="checkbox"
          checked={confirmado}
          onChange={(e) => setConfirmado(e.target.checked)}
        />
        <span>Confirmo os niveis de SL/TP e o risco financeiro desta operacao.</span>
      </label>

      <button
        type="button"
        className={`boleta-enviar ${lado === 'COMPRA' ? 'compra' : 'venda'}`}
        disabled={!podeEnviar}
        onClick={() => {
          if (!podeEnviar || !onSolicitarOrdem) return;
          onSolicitarOrdem({
            symbol,
            tipo,
            lado,
            volume,
            preco: entrada,
            sl: calculo.sl,
            tp: calculo.tp,
            pontosSL,
            pontosTP,
            riscoEstimado: calculo.risco,
          });
        }}
      >
        {rotuloBotao}
      </button>
    </div>
  );
}
