// ===========================================================================
//  BANCA, NOTICIAS E ORDENS ABERTAS (18/11/2026)
// ===========================================================================
//  Le SO o estado que `useRealtimeLiveStore` ja derivou. Nenhum fetch aqui,
//  nenhuma escrita: esta tela nao opera.
//
//  O LIMITE DE PERDA DIARIA NAO E PRESUMIDO. Se o chamador nao informar o
//  limite, a linha diz "limite nao informado" em vez de inventar 3% — um
//  numero inventado vira sensacao de protecao, que e pior que a ausencia dele.
import type { Order, Position } from '../hooks/useAppStore';

const dinheiro = (v: number) =>
  `${v < 0 ? '-' : ''}$${Math.abs(v).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

export interface BancaProps {
  saldo: number;
  patrimonio: number;
  flutuante: number;
  margemLivre: number;
  limitePerdaDiariaPct?: number;
  perdaDiariaPct?: number;
  avisoNoticias?: string;
  atualizadoEm: string;
}

export function BankrollPanel({
  saldo,
  patrimonio,
  flutuante,
  margemLivre,
  limitePerdaDiariaPct,
  perdaDiariaPct,
  avisoNoticias,
  atualizadoEm,
}: BancaProps) {
  const temLimite = typeof limitePerdaDiariaPct === 'number';
  const usado = typeof perdaDiariaPct === 'number' ? perdaDiariaPct : 0;
  const estourou = temLimite && usado >= (limitePerdaDiariaPct as number);

  return (
    <div className="banca-painel">
      <div className="kpi-grid">
        <div className="panel-card">
          <div className="kpi-rotulo">SALDO</div>
          <div className="kpi-value">{dinheiro(saldo)}</div>
        </div>
        <div className="panel-card">
          <div className="kpi-rotulo">PATRIMONIO</div>
          <div className="kpi-value kpi-info">{dinheiro(patrimonio)}</div>
        </div>
        <div className="panel-card">
          <div className="kpi-rotulo">FLUTUANTE</div>
          <div className={`kpi-value ${flutuante >= 0 ? 'kpi-positivo' : 'kpi-negativo'}`}>
            {flutuante >= 0 ? '+' : ''}
            {dinheiro(flutuante)}
          </div>
        </div>
        <div className="panel-card">
          <div className="kpi-rotulo">MARGEM LIVRE</div>
          <div className="kpi-value">{dinheiro(margemLivre)}</div>
        </div>
      </div>

      <div className={`banca-faixa ${estourou ? 'banca-faixa-alerta' : ''}`}>
        <strong>Perda diaria:</strong>{' '}
        {temLimite
          ? `${usado.toFixed(2)}% de ${Number(limitePerdaDiariaPct).toFixed(2)}%`
          : 'limite nao informado pelo gateway'}
        <span className="banca-faixa-hora">atualizado as {atualizadoEm}</span>
      </div>

      <div className="banca-faixa banca-faixa-noticia">
        <strong>Noticias:</strong>{' '}
        {avisoNoticias?.trim() || 'nenhum bloqueio informado pelo gateway.'}
      </div>
    </div>
  );
}

export interface OrdersProps {
  ordens: Order[];
  posicoes: Position[];
}

const ladoDaPosicao = (side: string): 'compra' | 'venda' | 'nao informado' => {
  const s = String(side || '').toLowerCase();
  if (s === 'buy' || s === 'compra' || s === '0') return 'compra';
  if (s === 'sell' || s === 'venda' || s === '1') return 'venda';
  return 'nao informado';
};

export function OrdersPanel({ ordens, posicoes }: OrdersProps) {
  return (
    <div className="ordens-painel">
      <h3 className="ordens-subtitulo">Posicoes abertas ({posicoes.length})</h3>
      <div className="table-scroll-wrapper">
        <table>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Ativo</th>
              <th>Lado</th>
              <th>Volume</th>
              <th>Entrada</th>
              <th>Atual</th>
              <th>Lucro</th>
            </tr>
          </thead>
          <tbody>
            {posicoes.length === 0 ? (
              <tr>
                <td colSpan={7} className="tabela-vazia">
                  Nenhuma posicao aberta.
                </td>
              </tr>
            ) : (
              posicoes.map((p) => {
                const lado = ladoDaPosicao(p.side);
                return (
                  <tr key={p.ticket}>
                    <td>#{p.ticket}</td>
                    <td>
                      <span className="symbol-badge">{p.symbol}</span>
                    </td>
                    <td className={`lado-${lado}`}>{lado}</td>
                    <td>{Number(p.volume ?? 0).toFixed(2)}</td>
                    <td>{Number(p.open_price ?? 0).toFixed(2)}</td>
                    <td>{Number(p.current_price ?? 0).toFixed(2)}</td>
                    <td className={Number(p.profit ?? 0) >= 0 ? 'kpi-positivo' : 'kpi-negativo'}>
                      {dinheiro(Number(p.profit ?? 0))}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <h3 className="ordens-subtitulo">Ordens pendentes ({ordens.length})</h3>
      <div className="table-scroll-wrapper">
        <table>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Ativo</th>
              <th>Tipo</th>
              <th>Volume</th>
              <th>Preco</th>
              <th>SL</th>
              <th>TP</th>
            </tr>
          </thead>
          <tbody>
            {ordens.length === 0 ? (
              <tr>
                <td colSpan={7} className="tabela-vazia">
                  Nenhuma ordem pendente.
                </td>
              </tr>
            ) : (
              ordens.map((o) => (
                <tr key={o.ticket}>
                  <td>#{o.ticket}</td>
                  <td>
                    <span className="symbol-badge">{o.symbol}</span>
                  </td>
                  <td>{o.type}</td>
                  <td>{Number(o.volume ?? 0).toFixed(2)}</td>
                  <td>{Number(o.price ?? 0).toFixed(2)}</td>
                  <td>{Number(o.sl ?? 0).toFixed(2)}</td>
                  <td>{Number(o.tp ?? 0).toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
