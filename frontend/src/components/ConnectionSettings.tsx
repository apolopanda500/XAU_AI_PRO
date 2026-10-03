import { useEffect, useState } from 'react';
import {
  connectionAction, detectTerminal, exigePassphrase, marketsFor, requestConnection,
  saveExchange, ROTULO_BROKER, type Broker, type Connection, type TerminalAccount,
} from '../lib/connections';

const TODAS: Broker[] = ['mt5', 'binance', 'mexc', 'bybit', 'okx'];

export default function ConnectionSettings() {
  const [broker, setBroker] = useState<Broker>('mt5');
  const [market, setMarket] = useState('');
  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [secret, setSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [rows, setRows] = useState<Connection[]>([]);
  const [account, setAccount] = useState<TerminalAccount | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [verified, setVerified] = useState<Record<string, string>>({});
  const precisaPassphrase = exigePassphrase(broker);
  const load = async () => {
    const data = await requestConnection('/api/connections');
    setRows(data.connections ?? []);
  };
  const sync = async () => {
    setAccount(null);
    const current = await detectTerminal();
    setAccount(current);
    setStatus(`MT5 sincronizado: ${current.login} · ${current.server}.`);
  };
  useEffect(() => {
    let active = true;
    requestConnection('/api/connections').then(data => {
      if (active) setRows(data.connections ?? []);
    }).catch(() => { if (active) setStatus('Gateway indisponível. Tente novamente.'); });
    detectTerminal().then(current => {
      if (active) setAccount(current);
    }).catch(() => { if (active) setAccount(null); });
    return () => { active = false; };
  }, []);
  const run = async (task: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setStatus('Verificando…');
    try { await task(); }
    catch (error) { setStatus(error instanceof Error ? error.message : 'Falha na comunicação com o gateway.'); }
    finally { setBusy(false); }
  };
  // Trocar de corretora limpa o segredo: a passphrase de uma exchange nao
  // pertence a outra, e manter o campo preenchido convida a gravar errado.
  const trocaBroker = (proxima: Broker) => {
    setBroker(proxima);
    setMarket(marketsFor(proxima)[0] ?? '');
    setKey(''); setSecret(''); setPassphrase(''); setStatus('');
  };
  // MT5 GRAVA A CONEXAO COMO AS OUTRAS (2026-09-30)
  //
  // Antes: `if (broker === 'mt5') { await sync(); return; }` — o MT5 lia a
  // sessao e nao criava registro nenhum. A linha dele era filtrada da tabela
  // (linha 113), entao o operador via as exchanges e nao via o proprio
  // terminal. Isso e MT5 como caminho paralelo, que e a regra que o projeto
  // proibe: a diferenca real dele e o CAMPO (login/servidor em vez de
  // API key), nao o fluxo.
  //
  // O nome da conexao do MT5 vem do proprio terminal, para o operador nao
  // ter que inventar um apelido so para a linha aparecer.
  const save = async () => {
    if (broker === 'mt5') {
      const current = await detectTerminal();
      setAccount(current);
      const rotulo = [current.name, String(current.server)].filter(Boolean).join(' @ ') || `conta ${current.login}`;
      const id = await saveExchange(broker, market, rotulo, '', '');
      await load();
      await connectionAction(id, 'test');
      setVerified(values => ({ ...values, [id]: 'Sessão do terminal' }));
      setStatus(`MT5 sincronizado: ${current.login} · ${current.server}. Conexão registrada como as demais.`);
      return;
    }
    const id = await saveExchange(broker, market, name, key, secret, passphrase);
    setKey(''); setSecret(''); setPassphrase('');
    await load();
    try {
      await connectionAction(id, 'test');
      setVerified(values => ({ ...values, [id]: 'Leitura validada' }));
      setStatus('Credenciais salvas e leitura da conta validada. Nenhuma ordem foi enviada.');
    } catch {
      setVerified(values => ({ ...values, [id]: 'Falha na validação' }));
      throw new Error('Credenciais salvas, mas a conexão não foi validada. Confira permissões de leitura, restrições de IP e mercado.');
    }
  };
  const action = async (id: string, command: 'test' | 'activate' | 'deactivate') => {
    setVerified(values => ({ ...values, [id]: 'Não verificada' }));
    await connectionAction(id, command);
    await load();
    setVerified(values => ({ ...values, [id]: command === 'deactivate' ? 'Desativada' : 'Leitura validada' }));
    setStatus(command === 'deactivate' ? 'Conexão desativada no aplicativo.' : 'Leitura da conta validada.');
  };

  return <div className="card compact-card connection-manager">
    <h2>Contas e conexões</h2>
    <p className="muted">MT5 usa a sessão do terminal. Binance e MEXC usam API key e secret. Validar leitura não autoriza negociação.</p>
    <fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
      <div className="order-ticket-grid">
        <label className="field">Corretora<select value={broker} onChange={event => trocaBroker(event.target.value as Broker)}>
          {TODAS.map(value => <option key={value} value={value}>{ROTULO_BROKER[value]}</option>)}
        </select></label>
        <label className="field">Mercado<select value={market} onChange={event => setMarket(event.target.value)}>
          {marketsFor(broker).map(value => <option key={value} value={value}>{value}</option>)}
        </select></label>
        {broker === 'mt5' ? <>
          <label className="field">Login do terminal<input readOnly value={account?.login ?? ''} placeholder="Nenhuma sessão detectada" /></label>
          <label className="field">Servidor<input readOnly value={account?.server ?? ''} /></label>
        </> : <>
          <label className="field">Nome<input value={name} onChange={event => setName(event.target.value)} /></label>
          <label className="field">API key<input type="password" autoComplete="off" value={key} onChange={event => setKey(event.target.value)} /></label>
          <label className="field">Secret<input type="password" autoComplete="off" value={secret} onChange={event => setSecret(event.target.value)} /></label>
          {precisaPassphrase && (
            <label className="field" title="A OKX recusa a conexão sem a passphrase criada junto com a API key">
              <span>Passphrase</span>
              <input type="password" autoComplete="off" value={passphrase} onChange={event => setPassphrase(event.target.value)} />
            </label>
          )}
        </>}
      </div>
      {broker !== 'mt5' && precisaPassphrase && (
        <p className="hint">A {ROTULO_BROKER[broker]} exige a passphrase gerada junto com a API key. Sem ela a corretora recusa a leitura.</p>
      )}
      {broker === 'mt5' && <p>Entre na conta pelo MetaTrader 5. O aplicativo detecta a sessão existente, sem guardar senha, trocar contas ou controlar o EA.</p>}
      <button type="button" className="btn primary" onClick={() => void run(save)}>{broker === 'mt5' ? 'Sincronizar MT5' : 'Salvar e validar API'}</button>
    </fieldset>
    <p role="status" aria-live="polite">{status}</p>
    <div className="table-scroll"><table className="tbl compact-table">
      <thead><tr><th>Conexão</th><th>Corretora</th><th>Mercado</th><th>Estado</th><th>Ações</th></tr></thead>
      <tbody>{rows.map(row => <tr key={row.id}>
        <td>{row.id.split(':').slice(2).join(':')}</td><td>{row.broker.toUpperCase()}</td><td>{row.market}</td>
        <td>{row.active === false ? 'Desativada' : verified[row.id] ?? 'Salva · não verificada'}</td>
        <td><button disabled={busy} className="btn xs ghost" onClick={() => void run(() => action(row.id, 'test'))}>Testar leitura</button>
          <button disabled={busy} className="btn xs ghost" onClick={() => void run(() => action(row.id, row.active === false ? 'activate' : 'deactivate'))}>{row.active === false ? 'Ativar' : 'Desativar'}</button>
          <button disabled={busy} className="btn xs danger" onClick={() => {
            if (!window.confirm('Excluir as credenciais desta conexão do aplicativo?')) return;
            void run(async () => { await requestConnection(`/api/connections/${encodeURIComponent(row.id)}`, 'DELETE'); await load(); setStatus('Conexão excluída.'); });
          }}>Excluir conexão</button></td>
      </tr>)}</tbody>
    </table></div>
  </div>;
}
