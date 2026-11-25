import { useCallback, useEffect, useState } from 'react';
import {
  detectTerminal,
  marketsFor,
  requestConnection,
  type Connection,
  type TerminalAccount,
} from '../lib/connections';
import { contaAtivaId, definirEscopoAtivo } from '../lib/escopoAtivo';
import {
  mercadoDoIdMt5,
  resumoSincronizacaoMt5,
  sincronizarMercadosMt5,
} from '../lib/sincronizarMt5';

/*
  CONTA MT5 — O UNICO PASSO QUE SOBRA PARA O USUARIO DO APK
  ========================================================
  O APK ja nasce apontando para o gateway (VITE_API_BASE) e autenticado
  (VITE_GATEWAY_TOKEN). Nao existe login de conta do app, nem campo de URL,
  nem senha: a credencial do MT5 e a SESSAO ABERTA NO PC, e o gateway a le.

  Este painel usa EXATAMENTE o caminho ja usado pelo ConnectionSettings —
  as mesmas funcoes de `lib/connections`, reunidas em `sincronizarMt5`:

    detectTerminal()  -> GET  /api/status        (conta logada no terminal)
    saveExchange()    -> POST /api/connections   (registra CADA mercado, sem segredo)
    connectionAction()-> POST /api/connections/{id}/test  (leitura, sem ordem)

  UM CLIQUE, TODOS OS MERCADOS (25/11/2026): antes so `marketsFor('mt5')[0]`
  era registrado e o operador via uma linha (forex) e achava que era so isso.
  O catalogo da corretora tem nove mercados — forex, metais, indices, acoes,
  commodities, titulos, cripto spot, cripto futuros e outros — e a sessao MT5
  serve todos eles (`connection_store.resolve_connection`).

  MT5 e uma corretora de SESSAO: `connection_service._gravar` grava a conexao
  sem API key e devolve `credential_source: "session"`. Por isso nao ha campo
  de senha aqui — pedir senha no celular seria pedir um segredo que o gateway
  nunca usa e que a tela nao deve transportar.
*/

const MERCADO_MT5 = marketsFor('mt5')[0] ?? 'forex';

export default function MT5AccountsPanel() {
  const [contas, setContas] = useState<Connection[]>([]);
  const [detectada, setDetectada] = useState<TerminalAccount | null>(null);
  const [ativa, setAtiva] = useState('');
  const [status, setStatus] = useState('');
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    setErro('');
    try {
      const [dados, sessao] = await Promise.all([
        requestConnection('/api/connections'),
        detectTerminal().catch(() => null),
      ]);
      setContas(
        (dados.connections ?? []).filter(
          (conta: Connection) => conta.broker === 'mt5',
        ),
      );
      setDetectada(sessao);
      setAtiva(contaAtivaId());
    } catch {
      setErro('Nao foi possivel falar com o gateway. Verifique a conexao e tente de novo.');
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const sincronizar = async () => {
    if (ocupado) return;
    setOcupado(true);
    setErro('');
    setStatus('');
    try {
      // Preserva a escolha anterior quando ela ainda existe: sincronizar nao
      // pode trocar o mercado ativo do motor sem o operador pedir.
      const escolhidaAntes = contaAtivaId();
      const relatorio = await sincronizarMercadosMt5();
      const idAtivo = Object.values(relatorio.ids).includes(escolhidaAntes)
        ? escolhidaAntes
        : relatorio.ids[relatorio.mercados[0]];
      const mercadoAtivo = mercadoDoIdMt5(relatorio, idAtivo) ?? relatorio.mercados[0];
      definirEscopoAtivo('mt5', mercadoAtivo, idAtivo);
      setDetectada(relatorio.conta);
      setAtiva(idAtivo);
      setStatus(resumoSincronizacaoMt5(relatorio));
      await carregar();
    } catch (exc) {
      setErro(exc instanceof Error ? exc.message : 'Falha ao sincronizar a conta MT5.');
    } finally {
      setOcupado(false);
    }
  };

  const usar = (conta: Connection) => {
    definirEscopoAtivo('mt5', conta.market || MERCADO_MT5, conta.id);
    setAtiva(conta.id);
    setStatus(`${conta.id.split(':').slice(2).join(':') || conta.id} passa a ser a conta usada pelo app.`);
  };

  return (
    <div className="card compact-card connection-manager">
      <h2>Conta MT5</h2>
      <p className="muted">
        Um clique vincula a conta aberta no MetaTrader 5 a TODOS os mercados do
        terminal — forex, metais, indices, cripto e os demais — e mostra todos
        juntos abaixo. Nenhuma senha e enviada pelo celular e nenhuma ordem e
        enviada por esta tela.
      </p>

      {erro && <p className="auth-erro" role="alert">{erro}</p>}
      {status && <p className="hint" role="status">{status}</p>}

      <h3>Sessao detectada no terminal</h3>
      {detectada ? (
        <p className="hint con-ok">
          {detectada.login} · {detectada.server}
          {detectada.name ? ` · ${detectada.name}` : ''}
        </p>
      ) : (
        <p className="hint con-aviso">
          Nenhuma conta logada no terminal. Abra o MetaTrader 5 no computador, entre
          na conta e clique em Sincronizar MT5.
        </p>
      )}

      <div className="btn-row">
        <button
          type="button"
          className="btn primary"
          disabled={ocupado || !detectada}
          onClick={() => void sincronizar()}
        >
          {ocupado ? 'Sincronizando…' : 'Sincronizar MT5 (todos os mercados)'}
        </button>
        <button type="button" className="btn ghost" disabled={ocupado} onClick={() => void carregar()}>
          Atualizar
        </button>
      </div>

      <h3>Contas MT5 vinculadas · todos os mercados</h3>
      {contas.length === 0 ? (
        <p className="hint">Nenhuma conta MT5 registrada ainda.</p>
      ) : (
        <ul className="hint">
          {contas.map((conta) => {
            const emUso = ativa === conta.id;
            return (
              <li key={conta.id}>
                {conta.id.split(':').slice(2).join(':') || conta.id} · {conta.market}
                {conta.active === false ? ' · desativada' : ''}
                {emUso ? ' · EM USO' : ''}
                {!emUso && (
                  <button type="button" className="btn ghost" onClick={() => usar(conta)}>
                    Usar esta conta
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
