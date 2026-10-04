// Sub-aba VIPS: progressao por volume, medida no audit.jsonl real pelo
// gateway (`/api/vip/progress`). Modelada no PrimeXBT — ver
// `Docs/VIP_PROGRESSAO.md`.
//
// POR QUE A ESCADA E SEPARADA DO PLANO
// O plano (Free / VIP / VIPS) e preferencia local de recursos. A escada
// aqui e medida por VOLUME OPERADO, que e como as corretoras fazem: voce
// sobe porque operou, nao porque ativou uma etiqueta. Sao coisas diferentes
// e a tela mostra as duas sem misturar.
//
// NADA E PROMESSA NESTA TELA
// Os limiares em codigo sao de estrutura. O desconto que cada nivel concede
// depende de acordo comercial com a corretora e NAO e exibido aqui — a tela
// mostraria numero que o sistema nao pode cumprir.
import { useCallback, useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import '../theme/vips.css';

type Degrau = {
  id: string;
  nome: string;
  estado: 'alcancado' | 'atual' | 'futuro';
  percentual: number;
  minimo_por_grupo: Record<string, number>;
};

type Nivel = {
  nivel: string;
  nivel_nome: string;
  beneficios: string[];
  janela_dias: number;
  trava_dias: number;
  dias_ate_promocao: number;
  volume_por_grupo: Record<string, number>;
  escada?: Degrau[];
  total_degraus?: number;
  proximo: { id: string; nome: string; falta_por_grupo: Record<string, number> } | null;
  live_execution: boolean;
  withdrawals_enabled: boolean;
};

// O que o PLANO destrava, separado do que o VOLUME alcancou.
//
// ATE 02/10/2026 A ESCADA NAO DESTRAVAVA NADA
// ===========================================
// A tela mostrava os degraus e nada mais. O operador subia de VIP por volume
// e nenhuma feature abria — `vip_progress.progresso()` devolvia a escada mas
// nunca escrevia em `entitlements`. Era "rotulo sem lastro", o mesmo padrao
// que o `plano_gate.py` descreve: "a tela prometia plano pago e o produto nao
// mudava".
//
// `/api/acesso` e `backend/acesso.py`: a arvore unica que junta plano e
// volume. `multi_model` e false no Free por decisao do dono, com reforco
// duplo. `live_execution` e `withdrawals_enabled` vem False no payload — nem
// plano nem volume destravam dinheiro real.
type Acesso = {
  plano: string;
  multi_model: boolean;
  multi_models: number;
  live_execution: boolean;
  withdrawals_enabled: boolean;
  volume?: { disponivel?: boolean; motivo?: string };
};

const GRUPOS: Array<[string, string]> = [
  ['cripto', 'Cripto'],
  ['forex_cfd', 'Forex e CFD'],
];

function usd(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return '--';
  if (valor >= 1_000_000) return `$${(valor / 1_000_000).toFixed(1)}M`;
  if (valor >= 1_000) return `$${(valor / 1_000).toFixed(1)}k`;
  return `$${valor.toFixed(0)}`;
}

export default function VipsTab() {
  const [dados, setDados] = useState<Nivel | null>(null);
  const [erro, setErro] = useState('');
  const [acesso, setAcesso] = useState<Acesso | null>(null);

  const carregar = useCallback(async (signal?: AbortSignal) => {
    try {
      const base = apiBase();
      const resposta = await fetch(`${base}/api/vip/progress`, {
        signal: signal ?? AbortSignal.timeout(6000),
      });
      if (!resposta.ok) {
        // O status sozinho nao diz onde procurar. Um 404 aqui tem DUAS causas
        // possiveis e elas pedem acoes opostas: (1) a rota existe e faltou o
        // token -> 401 mascarado; (2) `apiBase()` aponta para uma porta que nao
        // expoe /api/* (o core Rust nao tem esta rota) -> 404 de verdade.
        // Sem dizer qual origem foi consultada, o operador so ve "404" e nao
        // sabe se recarregar, refazer login ou corrigir a URL do gateway.
        throw new Error(
          resposta.status === 404
            ? `${base} não expõe /api/vip/progress — o gateway atende em http://127.0.0.1:9001. Confira a URL do gateway na tela de conexão.`
            : resposta.status === 401
              ? `${base} recusou: token ausente ou expirado. Refaça o login.`
              : `${base} respondeu ${resposta.status}.`,
        );
      }
      setDados((await resposta.json()) as Nivel);
      setErro('');
      // A escada e o que o VOLUME alcancou; o acesso e o que o PLANO destrava.
      // Sao duas chamadas porque sao duas fontes: `vip_progress` le o
      // audit.jsonl, `acesso` le a assinatura local. A tela precisa das duas
      // para nao mostrar degrau que nao abre nada.
      try {
        const r2 = await fetch(`${base}/api/acesso`, {
          signal: signal ?? AbortSignal.timeout(6000),
        });
        if (r2.ok) setAcesso((await r2.json()) as Acesso);
      } catch {
        // A escada continua util sem o acesso. Falhar aqui nao pode apagar a
        // tela inteira — o operador ainda precisa ver onde esta.
      }
    } catch (e) {
      if (signal?.aborted) return;
      setErro(e instanceof Error ? e.message : 'gateway indisponível');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void carregar(controller.signal);
    return () => controller.abort();
  }, [carregar]);

  return (
    <section className="vips" aria-labelledby="vips-title">
      <div className="section-head">
        <div>
          <h2 id="vips-title">Progressão VIP</h2>
          <span className="muted">
            Nível por volume executado na janela de {dados?.janela_dias ?? 30} dias
          </span>
        </div>
        {dados && <span className="chip">{dados.nivel_nome}</span>}
      </div>

      {/* O que o plano ABRE, separado do que o volume ALCANCOU. Sem este bloco
          a escada parece promocao e nao destrava nada — que era exatamente
          o defeito de 02/10/2026. */}
      {acesso && (
        <div className="section-head" style={{ marginTop: 8 }}>
          <div>
            <h3>O que seu plano destrava</h3>
            <span className="muted">Plano atual: {acesso.plano}</span>
          </div>
          <span className={`chip ${acesso.multi_model ? 'ok' : 'warn'}`}>
            {acesso.multi_model
              ? `Modelo multi liberado (${acesso.multi_models})`
              : 'Modelo único — multi no VIP'}
          </span>
        </div>
      )}

      {erro && (
        <p className="hint" role="status">
          {erro}
        </p>
      )}

      {dados && (
        <>
          <div className="vips-nivel">
            <strong>{dados.nivel_nome}</strong>
            <ul className="vips-beneficios">
              {dados.beneficios.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>

          {dados.escada && dados.escada.length > 0 && (
            <ol className="vips-escada" aria-label="Escada de níveis por volume">
              {dados.escada.map((degrau) => (
                <li key={degrau.id} className={`vips-degrau is-${degrau.estado}`}>
                  <div className="vips-degrau-topo">
                    <span className="vips-degrau-nome">{degrau.nome}</span>
                    {degrau.estado === 'alcancado' && <span className="vips-marca">alcançado</span>}
                    {degrau.estado === 'atual' && <span className="vips-marca atual">próximo</span>}
                    <span className="vips-degrau-pct">{degrau.percentual.toFixed(1)}%</span>
                  </div>
                  {/* A barra mostra quanto do degrau foi feito. `aria-hidden`
                      porque o numero ja esta em texto ao lado — leitor de
                      tela leria "barra" sem contexto. */}
                  <div
                    className="vips-barra"
                    role="img"
                    aria-label={`${degrau.percentual.toFixed(1)} por cento de ${degrau.nome}`}
                  >
                    <span style={{ width: `${Math.max(0, Math.min(100, degrau.percentual))}%` }} />
                  </div>
                  <div className="vips-degrau-min">
                    {GRUPOS.map(([chave, rotulo]) => (
                      <span key={chave}>
                        {rotulo}: {usd(degrau.minimo_por_grupo?.[chave])}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ol>
          )}

          {dados.proximo ? (
            <table className="tbl compact-table vips-tabela">
              <caption className="sr-only">
                Volume por grupo e quanto falta para {dados.proximo.nome}
              </caption>
              <thead>
                <tr>
                  <th>Grupo</th>
                  <th className="num">Volume na janela</th>
                  <th className="num">Falta para {dados.proximo.nome}</th>
                </tr>
              </thead>
              <tbody>
                {GRUPOS.map(([chave, rotulo]) => (
                  <tr key={chave}>
                    <td>{rotulo}</td>
                    <td className="num">{usd(dados.volume_por_grupo?.[chave])}</td>
                    <td className="num">{usd(dados.proximo?.falta_por_grupo?.[chave])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="hint">Nível máximo da escada atingido.</p>
          )}

          <p className="hint">
            Nível alcançado trava por {dados.trava_dias} dias. A promoção não é imediata: o nível
            novo vale a partir do dia seguinte ({dados.dias_ate_promocao} dia), como na Interactive
            Brokers.
          </p>
          <p className="hint">
            Os limiares são de estrutura: o desconto de cada nível depende de acordo com a corretora
            e não é exibido aqui.
          </p>
          <p className="hint">
            Saque e transferência: <b>{dados.withdrawals_enabled ? 'ATIVADO' : 'desativados'}</b> ·
            execução real: <b>{dados.live_execution ? 'ATIVADA' : 'desativada'}</b>
          </p>
        </>
      )}
    </section>
  );
}
