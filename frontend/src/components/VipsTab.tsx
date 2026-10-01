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

type Nivel = {
  nivel: string;
  nivel_nome: string;
  beneficios: string[];
  janela_dias: number;
  trava_dias: number;
  dias_ate_promocao: number;
  volume_por_grupo: Record<string, number>;
  proximo: { id: string; nome: string; falta_por_grupo: Record<string, number> } | null;
  live_execution: boolean;
  withdrawals_enabled: boolean;
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

  const carregar = useCallback(async (signal?: AbortSignal) => {
    try {
      const resposta = await fetch(`${apiBase()}/api/vip/progress`, { signal: signal ?? AbortSignal.timeout(6000) });
      if (!resposta.ok) throw new Error(`gateway respondeu ${resposta.status}`);
      setDados(await resposta.json() as Nivel);
      setErro('');
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
          <span className="muted">Nível por volume executado na janela de {dados?.janela_dias ?? 30} dias</span>
        </div>
        {dados && <span className="chip">{dados.nivel_nome}</span>}
      </div>

      {erro && <p className="hint" role="status">{erro}</p>}

      {dados && (
        <>
          <div className="vips-nivel">
            <strong>{dados.nivel_nome}</strong>
            <ul className="vips-beneficios">
              {dados.beneficios.map((b) => <li key={b}>{b}</li>)}
            </ul>
          </div>

          {dados.proximo ? (
            <table className="tbl compact-table vips-tabela">
              <caption className="sr-only">Volume por grupo e quanto falta para {dados.proximo.nome}</caption>
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
            Nível alcançado trava por {dados.trava_dias} dias. A promoção não é
            imediata: o nível novo vale a partir do dia seguinte ({dados.dias_ate_promocao} dia),
            como na Interactive Brokers.
          </p>
          <p className="hint">
            Os limiares são de estrutura: o desconto de cada nível depende de acordo
            com a corretora e não é exibido aqui.
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
