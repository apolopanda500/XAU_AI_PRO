// Central de comando movel - SOMENTE LEITURA (17/11/2026).
//
// POR QUE ESTA TELA NAO TEM BOTAO DE ORDEM
// ========================================
// O celular e o caminho mais curto entre um toque acidental e uma ordem real:
// tela no bolso, dedo molhado, botao de 44 px ao lado de outro. O gateway ja
// recusa escrita em `THIRD_PARTY_READ_ONLY` e exige token em toda rota; um
// painel movel com "comprar/vender" passaria por cima das duas guardas, porque
// falaria com o gateway JA autenticado.
//
// A regra do projeto e explicita: `withdrawals_enabled` e `False` fixo e
// nenhuma refatoracao pode torna-lo condicional. Aqui a mesma linha vale para
// execucao: a tela LE conta, posicoes, ordens, risco e saude, e nada mais.
//
// O DEFEITO QUE ESTE ARQUIVO EVITA
// ================================
// MEDIDO no projeto: 401, 429 e "nenhuma corretora" ja produziram a MESMA tela
// vazia (ver `LatenciaBar.tsx`). Ausencia renderizada como NADA e indistinguivel
// de ausencia real, e o operador culpa a coisa errada. Portanto:
//   - cada bloco diz `ok` e `motivo`;
//   - os tres estados de falha tem frase propria (sem sessao, cota, gateway);
//   - o selo "somente leitura" aparece SEMPRE, inclusive em erro - ele e a
//     informacao mais importante da tela.
//
// FAIL-CLOSED DO LADO DO CLIENTE
// ------------------------------
// Se o gateway responder `read_only: false` ou `commands_enabled: true`, esta
// tela NAO exibe os dados e denuncia a divergencia. Um servidor mal
// configurado nao vira permissao no cliente. Prova negativa em
// `MobileCommandCenter.test.tsx`.
import React, { useCallback, useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { clsPnl, fmtMoney, fmtNum, fmtPct } from '../lib/format';
import '../theme/mobile-command-center.css';

type Lado = 'compra' | 'venda' | 'desconhecido';

type Conta = {
  ok: boolean;
  motivo: string;
  login: number | string | null;
  servidor: string;
  corretora: string;
  moeda: string;
  saldo: number | null;
  equity: number | null;
  margem_livre: number | null;
  alavancagem: number | null;
};

type Posicao = {
  ticket: number | string | null;
  simbolo: string;
  lado: Lado;
  volume: number | null;
  preco_abertura: number | null;
  preco_atual: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lucro: number | null;
  comentario: string;
};

type Ordem = {
  ticket: number | string | null;
  simbolo: string;
  lado: Lado;
  volume: number | null;
  preco: number | null;
  stop_loss: number | null;
  take_profit: number | null;
};

type Saude = {
  ok: boolean;
  motivo: string;
  gateway_build: string;
  uptime_sec: number | null;
  terminal_connected: boolean | null;
};

type Risco = {
  ok: boolean;
  motivo: string;
  risco_por_operacao_pct: number | null;
  perda_diaria_pct: number | null;
  perda_diaria_limite_pct: number | null;
  drawdown_pct: number | null;
  drawdown_limite_pct: number | null;
  bloqueios: string[];
};

type Retrato = {
  ok: boolean;
  read_only: boolean;
  commands_enabled: boolean;
  execution_enabled: boolean;
  withdrawals_enabled: boolean;
  gerado_em: number;
  conta: Conta;
  posicoes: {
    ok: boolean;
    disponivel: boolean;
    motivo: string;
    total: number;
    lidos: number;
    recusadas: number;
    itens: Posicao[];
  };
  ordens: { ok: boolean; disponivel: boolean; motivo: string; total: number; recusadas: number; itens: Ordem[] };
  saude: Saude;
  risco: Risco;
  avisos: string[];
  comandos_recusados: string[];
};

// Os estados de leitura. Cada um tem uma frase propria: e a diferenca entre
// "nao ha posicao" e "nao consegui perguntar".
type Estado = 'medindo' | 'ok' | 'sem-sessao' | 'cota' | 'indisponivel' | 'divergente';

const INTERVALO_MS = 10_000;

/** Le o status ANTES do corpo: 401 e 429 vem com `{ok:false}` e escondem a causa. */
async function buscarRetrato(): Promise<{ status: number; corpo: unknown }> {
  const resposta = await fetch(`${apiBase()}/api/mobile/control`, {
    signal: AbortSignal.timeout(8_000),
  });
  const status = resposta.status;
  const corpo = await resposta.json().catch(() => null);
  return { status, corpo };
}

/** Um retrato so e aceito se o servidor declarar leitura. Nada e presumido. */
function ehRetratoSeguro(corpo: unknown): corpo is Retrato {
  if (!corpo || typeof corpo !== 'object') return false;
  const r = corpo as Partial<Retrato>;
  return r.read_only === true && r.commands_enabled === false;
}

function Linha({ rotulo, valor, classe }: { rotulo: string; valor: string; classe?: string }) {
  return (
    <div className="mcc-linha">
      <span className="mcc-rotulo">{rotulo}</span>
      <span className={`mcc-valor ${classe ?? ''}`}>{valor}</span>
    </div>
  );
}

function Lado({ lado }: { lado: Lado }) {
  // "desconhecido" existe de proposito: rotular uma venda como compra (o que
  // `sideOfPosition` de `lib/format.ts` faz por padrao) e pior que nao rotular.
  const texto = lado === 'compra' ? 'compra' : lado === 'venda' ? 'venda' : 'lado nao informado';
  return <span className={`mcc-lado mcc-lado-${lado}`}>{texto}</span>;
}

export default function MobileCommandCenter({ intervaloMs = INTERVALO_MS }: { intervaloMs?: number }) {
  const [retrato, setRetrato] = useState<Retrato | null>(null);
  const [estado, setEstado] = useState<Estado>('medindo');

  const ler = useCallback(async () => {
    try {
      const { status, corpo } = await buscarRetrato();
      if (status === 401) {
        // Sem sessao NAO e "sem dados": o celular precisa dizer que o login
        // caiu, senao o operador acha que a conta esta vazia.
        setEstado('sem-sessao');
        return;
      }
      if (status === 429) {
        // Cota do minuto, nao corretora fora do ar.
        setEstado('cota');
        return;
      }
      if (status === 403) {
        setEstado('divergente');
        setRetrato(null);
        return;
      }
      if (status >= 500) {
        // 503 e o gateway SE declarando indisponivel (MT5 sem resposta). E o
        // mesmo estado de rede fora aos olhos do operador: nao ha dado agora.
        setEstado('indisponivel');
        return;
      }
      if (!ehRetratoSeguro(corpo)) {
        // Duas causas possiveis, e as duas aparecem como divergencia: corpo
        // invalido, ou servidor declarando escrita habilitada.
        setEstado('divergente');
        setRetrato(null);
        return;
      }
      setRetrato(corpo);
      setEstado('ok');
    } catch {
      setEstado('indisponivel');
    }
  }, []);

  useEffect(() => {
    let vivo = true;
    const ciclo = () => {
      if (vivo) void ler();
    };
    ciclo();
    const timer = setInterval(ciclo, Math.max(2_000, intervaloMs));
    return () => {
      vivo = false;
      clearInterval(timer);
    };
  }, [ler, intervaloMs]);

  const FRASES: Record<Estado, { titulo: string; texto: string }> = {
    medindo: { titulo: 'Medindo', texto: 'primeira leitura em andamento' },
    ok: { titulo: 'Ao vivo', texto: 'retrato da conta ativa' },
    'sem-sessao': {
      titulo: 'Sem sessao',
      texto: 'o gateway recusou a leitura (401). Entre novamente para ver a conta.',
    },
    cota: {
      titulo: 'Cota do minuto',
      texto: 'o gateway devolveu 429: cota de leitura estourada. Nao e a corretora fora do ar.',
    },
    indisponivel: {
      titulo: 'Gateway fora',
      texto: 'sem resposta do gateway. Confira o endereco configurado na tela de conexao.',
    },
    divergente: {
      titulo: 'Leitura recusada',
      texto:
        'o gateway nao declarou somente leitura (ou respondeu 403). Esta tela nao exibe dados nesse estado.',
    },
  };

  const selo = (
    <div className="mcc-selo" role="status" title="Esta tela nao envia ordem, nao fecha posicao e nao movimenta saldo">
      <span className="mcc-selo-ponto" aria-hidden="true" />
      SOMENTE LEITURA
    </div>
  );

  if (estado !== 'ok' || !retrato) {
    const frase = FRASES[estado];
    return (
      <section className="mcc" aria-label="Central de comando movel">
        <header className="mcc-topo">
          <h2 className="mcc-titulo">Central de comando</h2>
          {selo}
        </header>
        <div className={`mcc-aviso mcc-aviso-${estado}`}>
          <strong>{frase.titulo}</strong>
          <span>{frase.texto}</span>
        </div>
      </section>
    );
  }

  const { conta, posicoes, ordens, risco, saude, avisos } = retrato;
  const pnlTotal = posicoes.itens.reduce((soma, p) => soma + (p.lucro ?? 0), 0);
  const temLucro = posicoes.itens.some((p) => p.lucro !== null);

  return (
    <section className="mcc" aria-label="Central de comando movel">
      <header className="mcc-topo">
        <h2 className="mcc-titulo">Central de comando</h2>
        {selo}
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* CONTA                                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="mcc-bloco">
        <div className="mcc-bloco-topo">
          <h3>Conta</h3>
          <span className={`mcc-tag ${conta.ok ? 'ok' : 'falta'}`}>{conta.ok ? 'lida' : 'sem dado'}</span>
        </div>
        {conta.ok ? (
          <>
            <Linha rotulo="Login" valor={conta.login === null ? '--' : String(conta.login)} />
            <Linha rotulo="Servidor" valor={conta.servidor || '--'} />
            <Linha rotulo="Corretora" valor={conta.corretora || '--'} />
            <Linha rotulo="Saldo" valor={fmtMoney(conta.saldo, conta.moeda)} />
            <Linha
              rotulo="Equity"
              valor={fmtMoney(conta.equity, conta.moeda)}
              classe={conta.equity !== null && conta.saldo !== null ? clsPnl(conta.equity - conta.saldo) : ''}
            />
            <Linha rotulo="Margem livre" valor={fmtMoney(conta.margem_livre, conta.moeda)} />
            <Linha rotulo="Alavancagem" valor={conta.alavancagem === null ? '--' : `1:${fmtNum(conta.alavancagem, 0)}`} />
          </>
        ) : (
          <p className="mcc-motivo">{conta.motivo}</p>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* POSICOES                                                         */}
      {/* ---------------------------------------------------------------- */}
      <div className="mcc-bloco">
        <div className="mcc-bloco-topo">
          <h3>Posicoes</h3>
          <span className={`mcc-tag ${posicoes.ok ? 'ok' : 'falta'}`}>
            {posicoes.ok ? `${posicoes.total} aberta${posicoes.total === 1 ? '' : 's'}` : 'sem leitura'}
          </span>
        </div>
        {posicoes.itens.length === 0 ? (
          <p className={posicoes.ok ? 'mcc-motivo' : 'mcc-motivo mcc-motivo-forte'}>
            {/*
              LISTA VAZIA TEM DUAS CAUSAS e elas nao podem ter o mesmo texto:
              "nao ha posicao" e "nao consegui perguntar". O operador que le a
              primeira quando a verdade e a segunda abre ordem achando que esta
              zerado.
            */}
            {!posicoes.ok
              ? posicoes.motivo || 'posicoes nao lidas'
              : posicoes.lidos === 0
                ? 'nenhuma posicao aberta na conta ativa'
                : 'nenhuma posicao legivel'}
          </p>
        ) : (
          <ul className="mcc-lista">
            {posicoes.itens.map((p) => (
              <li key={String(p.ticket ?? `${p.simbolo}-${p.volume}`)} className="mcc-item">
                <div className="mcc-item-topo">
                  <strong className="mcc-simbolo">{p.simbolo}</strong>
                  <Lado lado={p.lado} />
                  <span className="mcc-volume">{fmtNum(p.volume, 2)}</span>
                  <span className={`mcc-pnl ${p.lucro === null ? '' : clsPnl(p.lucro)}`}>
                    {p.lucro === null ? '--' : fmtNum(p.lucro, 2)}
                  </span>
                </div>
                <div className="mcc-item-detalhe">
                  <span>abertura {fmtNum(p.preco_abertura, 5)}</span>
                  <span>atual {fmtNum(p.preco_atual, 5)}</span>
                  <span>SL {fmtNum(p.stop_loss, 5)}</span>
                  <span>TP {fmtNum(p.take_profit, 5)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
        {posicoes.recusadas > 0 && <p className="mcc-motivo">{posicoes.motivo}</p>}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* ORDENS PENDENTES                                                 */}
      {/* ---------------------------------------------------------------- */}
      <div className="mcc-bloco">
        <div className="mcc-bloco-topo">
          <h3>Ordens pendentes</h3>
          <span className={`mcc-tag ${ordens.ok ? 'ok' : 'falta'}`}>{ordens.ok ? ordens.total : 'sem leitura'}</span>
        </div>
        {ordens.itens.length === 0 ? (
          <p className={ordens.ok ? 'mcc-motivo' : 'mcc-motivo mcc-motivo-forte'}>
            {ordens.ok ? 'nenhuma ordem pendente' : ordens.motivo || 'ordens nao lidas'}
          </p>
        ) : (
          <ul className="mcc-lista">
            {ordens.itens.map((o) => (
              <li key={String(o.ticket ?? `${o.simbolo}-${o.preco}`)} className="mcc-item">
                <div className="mcc-item-topo">
                  <strong className="mcc-simbolo">{o.simbolo}</strong>
                  <Lado lado={o.lado} />
                  <span className="mcc-volume">{fmtNum(o.volume, 2)}</span>
                  <span className="mcc-preco">{fmtNum(o.preco, 5)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
        {ordens.recusadas > 0 && <p className="mcc-motivo">{ordens.motivo}</p>}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* RISCO                                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="mcc-bloco">
        <div className="mcc-bloco-topo">
          <h3>Risco</h3>
          <span className={`mcc-tag ${risco.ok ? 'ok' : 'falta'}`}>{risco.ok ? 'lido' : 'sem dado'}</span>
        </div>
        {risco.ok ? (
          <>
            <Linha rotulo="Por operacao" valor={fmtPct(risco.risco_por_operacao_pct)} />
            <Linha
              rotulo="Perda do dia"
              valor={`${fmtPct(risco.perda_diaria_pct)} / ${fmtPct(risco.perda_diaria_limite_pct)}`}
            />
            <Linha
              rotulo="Drawdown"
              valor={`${fmtPct(risco.drawdown_pct)} / ${fmtPct(risco.drawdown_limite_pct)}`}
            />
            {risco.bloqueios.length > 0 && (
              <ul className="mcc-bloqueios">
                {risco.bloqueios.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <p className="mcc-motivo">{risco.motivo}</p>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SAUDE                                                            */}
      {/* ---------------------------------------------------------------- */}
      <div className="mcc-bloco mcc-bloco-saude">
        <div className="mcc-bloco-topo">
          <h3>Gateway</h3>
          <span className={`mcc-tag ${saude.ok ? 'ok' : 'falta'}`}>{saude.ok ? 'ok' : 'sem resposta'}</span>
        </div>
        {saude.ok ? (
          <>
            <Linha rotulo="Build" valor={saude.gateway_build || '--'} />
            <Linha
              rotulo="Terminal MT5"
              valor={
                saude.terminal_connected === null
                  ? 'nao informado'
                  : saude.terminal_connected
                    ? 'conectado'
                    : 'desconectado'
              }
              classe={saude.terminal_connected === false ? 'neg' : ''}
            />
            <Linha
              rotulo="No ar ha"
              valor={saude.uptime_sec === null ? '--' : `${fmtNum(saude.uptime_sec / 60, 0)} min`}
            />
            <Linha rotulo="Lucro das abertas" valor={temLucro ? fmtNum(pnlTotal, 2) : '--'} />
          </>
        ) : (
          <p className="mcc-motivo">{saude.motivo}</p>
        )}
      </div>

      {/* Avisos do servidor: recusa com motivo, nunca silencio. */}
      {avisos.length > 0 && (
        <div className="mcc-avisos" role="note">
          {avisos.map((a) => (
            <p key={a}>{a}</p>
          ))}
        </div>
      )}
    </section>
  );
}
