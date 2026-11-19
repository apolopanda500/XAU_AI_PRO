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
import { apiBase, isMobileRuntime, sessionToken } from '../lib/api';
import { exportarJson } from '../lib/mobileExport';
import { clsPnl, fmtMoney, fmtNum, fmtPct } from '../lib/format';
import MarketSessionsClock from './MarketSessionsClock';
import MobileLotCalculator from './MobileLotCalculator';
import MobilePermissionsHub from './MobilePermissionsHub';
import '../theme/mobile-command-center.css';

// GUARDRAIL FECHADO (19/11/2026): Central de Comando UMA SOLA no app.
// O marcador no document.head é a fonte única de verdade do dono do slot:
// uma segunda instância desliga, sem duplicar polls nem painéis.
const INSTANCE_ATTR = 'data-xau-command-center-mounted';

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
  const token = sessionToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const resposta = await fetch(`${apiBase()}/api/mobile/control`, {
    headers,
    signal: AbortSignal.timeout(8_000),
  });
  const status = resposta.status;
  const corpo = await resposta.json().catch(() => null);
  return { status, corpo };
}

/** O retrato só atravessa o fail-closed quando o servidor declara leitura
 *  OU declara destravar sob o modo `XAU_MOBILE_CONTROL_ENABLED=1`. */
function ehRetratoSeguro(corpo: unknown): corpo is Retrato {
  if (!corpo || typeof corpo !== 'object') return false;
  const r = corpo as Partial<Retrato>;
  const somenteLeitura =
    r.read_only === true && r.commands_enabled === false && r.execution_enabled === false;
  const destravado =
    r.read_only === false && r.commands_enabled === true && r.execution_enabled === true;
  return somenteLeitura || destravado;
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
  const [unlocked, setUnlocked] = useState(false);
  const [cmdMsg, setCmdMsg] = useState('');
  const [pending, setPending] = useState(false);
  const [riskPct, setRiskPct] = useState('0.5');
  const [dailyTarget, setDailyTarget] = useState('50');
  const [perfil, setPerfil] = useState('STANDARD');
  const [duplicada, setDuplicada] = useState(false);

  // GUARDRAIL FECHADO: se outra Central já estiver em DOM, desliga esta.
  useEffect(() => {
    const existente = document.querySelector(`[${INSTANCE_ATTR}="true"]`);
    if (existente) {
      setDuplicada(true);
      return;
    }
    const marcador = document.createElement('meta');
    marcador.setAttribute(INSTANCE_ATTR, 'true');
    document.head.appendChild(marcador);
    return () => {
      marcador.remove();
    };
  }, []);

  // Todos os hooks acima — a duplicada sai só na renderização (regra dos hooks).

  const enviarComando = useCallback(
    async (action: string, extra?: { value?: number; profile?: string }) => {
      if (pending) return;
      setPending(true);
      setCmdMsg('');
      try {
        const token = sessionToken();
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (token) headers.Authorization = `Bearer ${token}`;
        const resposta = await fetch(`${apiBase()}/api/mobile/command`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            action,
            value: extra?.value,
            profile: extra?.profile,
            command_id: `mob_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            confirm: true,
          }),
        });
        const corpo = (await resposta.json().catch(() => null)) as Record<string, unknown> | null;
        setCmdMsg(
          resposta.ok
            ? `Comando aceito: ${String(corpo?.action ?? action)}`
            : `Recusado (${resposta.status}): ${String(corpo?.error ?? 'falha no gateway')}`,
        );
      } catch (e) {
        setCmdMsg(e instanceof Error ? e.message : 'falha de rede');
      } finally {
        setPending(false);
      }
    },
    [pending],
  );

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

  const confirmarEEnviar = (action: string, extra?: { value?: number; profile?: string }) => {
    const alertas: Record<string, string> = {
      CLOSE_ALL_POSITIONS: 'Fechar TODAS as posições abertas?',
      MOVE_ALL_BREAKEVEN: 'Mover TODAS as posições para breakeven?',
      RESUME_AUTO: 'Ligar o robô automaticamente?',
      SET_RISK_PCT: `Alterar risco por operação para ${riskPct}%?`,
      SET_DAILY_TARGET_USD: `Alterar meta diária para US$ ${dailyTarget}?`,
      SET_PROP_PROFILE: `Alternar perfil Prop para ${perfil}?`,
    };
    if (!window.confirm(alertas[action] ?? action)) return;
    void enviarComando(action, extra);
  };

  const destravadoServidor = Boolean(retrato?.commands_enabled && retrato?.execution_enabled);

  const selo = destravadoServidor ? (
    <button
      type="button"
      className={`mcc-selo mcc-selo-unlock ${unlocked ? 'on' : ''}`}
      aria-pressed={unlocked}
      onClick={() => setUnlocked((v) => !v)}
      title={
        unlocked
          ? 'Tocar trava os controles novamente'
          : 'Habilita os botões de comando neste aparelho'
      }
    >
      <span className="mcc-selo-ponto" aria-hidden="true" />
      {unlocked ? 'CONTROLES ATIVOS' : 'DESTRAVAR COMANDOS'}
    </button>
  ) : (
    <div
      className="mcc-selo"
      role="status"
      title="Esta tela nao envia ordem, nao fecha posicao e nao movimenta saldo"
    >
      <span className="mcc-selo-ponto" aria-hidden="true" />
      SOMENTE LEITURA
    </div>
  );

  // GUARDRAIL FECHADO: uma Central só. Depois de todos os hooks (regra React).
  if (duplicada) return null;

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

      {destravadoServidor && unlocked && (
        <div className="mcc-bloco mcc-commands">
          <div className="mcc-bloco-topo">
            <h3>Comandos</h3>
            <span className="mcc-tag ok">liberado</span>
          </div>
          <div className="mcc-cmds-row">
            <button type="button" className="btn xs ghost" disabled={pending} onClick={() => confirmarEEnviar('PAUSE_AUTO')}>
              Pausar Auto
            </button>
            <button type="button" className="btn xs ghost" disabled={pending} onClick={() => confirmarEEnviar('RESUME_AUTO')}>
              Retomar Auto
            </button>
            <button type="button" className="btn xs ghost" disabled={pending} onClick={() => confirmarEEnviar('MOVE_ALL_BREAKEVEN')}>
              Break-even todas
            </button>
            <button type="button" className="btn xs danger" disabled={pending} onClick={() => confirmarEEnviar('CLOSE_ALL_POSITIONS')}>
              Fechar todas
            </button>
          </div>
          <div className="mcc-cmds-row">
            <label className="field field-inline">
              <span>Risco %</span>
              <input className="input" type="number" min={0.1} max={5.0} step={0.1} value={riskPct} onChange={(e) => setRiskPct(e.target.value)} />
            </label>
            <button type="button" className="btn xs primary" disabled={pending} onClick={() => confirmarEEnviar('SET_RISK_PCT', { value: Number(riskPct) })}>
              Setar risco
            </button>
          </div>
          <div className="mcc-cmds-row">
            <label className="field field-inline">
              <span>Meta diária US$</span>
              <input className="input" type="number" min={1} step={1} value={dailyTarget} onChange={(e) => setDailyTarget(e.target.value)} />
            </label>
            <button type="button" className="btn xs primary" disabled={pending} onClick={() => confirmarEEnviar('SET_DAILY_TARGET_USD', { value: Number(dailyTarget) })}>
              Setar alvo
            </button>
          </div>
          <div className="mcc-cmds-row">
            <label className="field field-inline">
              <span>Perfil</span>
              <select className="input" value={perfil} onChange={(e) => setPerfil(e.target.value)}>
                <option value="STANDARD">Standard</option>
                <option value="FTMO">FTMO</option>
                <option value="FUNDEDNEXT">FundedNext</option>
                <option value="THE5ERS">THE5ERS</option>
              </select>
            </label>
            <button type="button" className="btn xs primary" disabled={pending} onClick={() => confirmarEEnviar('SET_PROP_PROFILE', { profile: perfil })}>
              Aplicar perfil
            </button>
          </div>
          {cmdMsg && (
            <p className="hint" role="status" style={{ marginBottom: 0 }}>
              {cmdMsg}
            </p>
          )}
        </div>
      )}

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

      {isMobileRuntime() && (
        <div className="mcc-mobile-pro" style={{ display: 'grid', gap: 12 }}>
          <MarketSessionsClock />
          <MobileLotCalculator defaultBalance={conta.saldo ?? 13038.61} />
          <div className="mcc-bloco">
            <div className="mcc-bloco-topo">
              <h3>Exportação & Auditoria</h3>
              <span className="mcc-tag ok">mobile</span>
            </div>
            <p className="mcc-motivo" style={{ marginTop: 0 }}>
              Exporte um retrato somente leitura da conta, posições, ordens e risco para compartilhar ou arquivar.
            </p>
            <button
              type="button"
              className="btn sm"
              onClick={() => void exportarJson(`xau-ai-pro-auditoria-${Date.now()}`, retrato)}
            >
              Exportar auditoria (JSON)
            </button>
          </div>
          <MobilePermissionsHub />
        </div>
      )}
    </section>
  );
}
