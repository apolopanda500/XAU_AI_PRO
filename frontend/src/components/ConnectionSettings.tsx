import { useEffect, useMemo, useState } from 'react';
import EditarConexao from './EditarConexao';
import {
  connectionAction,
  detectTerminal,
  exigePassphrase,
  marketsFor,
  requestConnection,
  saveExchange,
  ROTULO_BROKER,
  type Broker,
  type Connection,
  type TerminalAccount,
} from '../lib/connections';

const TODAS: Broker[] = ['mt5', 'binance', 'mexc', 'bybit', 'okx'];

export default function ConnectionSettings() {
  const [broker, setBroker] = useState<Broker>('mt5');
  /*
    O MERCADO NASCE ESCOLHIDO (05/10/2026).

    Começava em `''`, e a pendência "Escolha o mercado" mantinha o botão de
    salvar cinza numa tela que já mostra corretora, mercado e campos prontos —
    sem nada visualmente faltando. O operador não tinha o que clicar para
    destravar.

    Agora nasce no primeiro mercado da corretora, exatamente como `trocaBroker`
    já fazia ao trocar de corretora. E não é presunção de ATIVO nem de
    CORRETORA: o mercado é a divisão que o app oferece para aquela corretora
    (`marketsFor`), e o operador troca numa linha se quiser outra.
  */
  const [market, setMarket] = useState<string>(() => marketsFor('mt5')[0] ?? '');
  const [name, setName] = useState('');
  const [server, setServer] = useState('');
  const [key, setKey] = useState('');
  const [secret, setSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [rows, setRows] = useState<Connection[]>([]);
  const [account, setAccount] = useState<TerminalAccount | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [verified, setVerified] = useState<Record<string, string>>({});
  const precisaPassphrase = exigePassphrase(broker);

  /**
   * O QUE FALTA PARA PODER SALVAR — escrito, não só desabilitado.
   *
   * MEDIDO (05/10/2026): o botão ficava `disabled` enquanto não houvesse NOME
   * digitado, e para MT5 o nome é OPCIONAL — `save()` usa o nome do terminal
   * quando o campo está vazio. Resultado: o operador que só queria sincronizar
   * a sessão do MT5 via um botão morto, sem nenhuma explicação na tela. É a
   * "dificuldade" de configurar conta.
   *
   * Botão desabilitado SEM dizer o que falta é um botão quebrado com aparência
   * de espera. Aqui a lista aparece junto do botão.
   */
  const pendencias = useMemo<string[]>(() => {
    const lista: string[] = [];
    if (!market) lista.push('Escolha o mercado');
    if (broker === 'mt5') {
      if (!account) lista.push('Abra e logue no MetaTrader 5 — nenhuma sessão detectada');
    } else {
      if (!name.trim()) lista.push('Dê um nome à conexão');
      if (!key.trim()) lista.push('Cole a API key');
      if (!secret.trim()) lista.push('Cole o secret');
      if (precisaPassphrase && !passphrase.trim()) lista.push('Cole a passphrase');
    }
    return lista;
  }, [market, broker, account, name, key, secret, passphrase, precisaPassphrase]);
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
    requestConnection('/api/connections')
      .then((data) => {
        if (active) setRows(data.connections ?? []);
      })
      .catch(() => {
        if (active) setStatus('Gateway indisponível. Tente novamente.');
      });
    detectTerminal()
      .then((current) => {
        if (active) setAccount(current);
      })
      .catch(() => {
        if (active) setAccount(null);
      });
    return () => {
      active = false;
    };
  }, []);
  const run = async (task: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setStatus('Verificando…');
    try {
      await task();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Falha na comunicação com o gateway.');
    } finally {
      setBusy(false);
    }
  };
  // Trocar de corretora limpa o segredo: a passphrase de uma exchange nao
  // pertence a outra, e manter o campo preenchido convida a gravar errado.
  //
  // O NOME tbem e limpo. Sem isso, ao voltar para a corretora anterior o
  // campo continuava com o rotulo da outra e o `id` gerado apontava para uma
  // conexao com nome trocado — conexao nova silenciosa a cada troca.
  const trocaBroker = (proxima: Broker) => {
    setBroker(proxima);
    setMarket(marketsFor(proxima)[0] ?? '');
    setName('');
    setServer('');
    setKey('');
    setSecret('');
    setPassphrase('');
    setStatus('');
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
      // O nome digitado manda; sem ele, o rotulo vem do terminal. Era o
      // unico jeito de distinguir duas conexoes de sessao, e o campo nao
      // existia para MT5 — agora existe para os dois caminhos.
      /*
        O ROTULO CARREGA O SERVIDOR, e isso e o que torna dois servidores
        distin��os. Sem ele, XMGlobal-MT5 14 e XMGlobal-MT5 20 produziriam
        rotulos iguais e a segunda conexao sobrescreveria a primeira — o
        operador veria uma linha e acharia que a outra foi perdida.
      */
      const servidorNome = server.trim() || String(current.server || '').trim();
      const rotulo =
        name.trim() ||
        [current.name, servidorNome].filter(Boolean).join(' @ ') ||
        `conta ${current.login}`;
      const id = await saveExchange(broker, market, rotulo, '', '');
      await load();
      await connectionAction(id, 'test');
      setVerified((values) => ({ ...values, [id]: 'Sessão do terminal' }));
      setStatus(
        `MT5 sincronizado: ${current.login} · ${current.server}. Conexão registrada como as demais.`,
      );
      return;
    }
    const id = await saveExchange(broker, market, name, key, secret, passphrase);
    setKey('');
    setSecret('');
    setPassphrase('');
    await load();
    try {
      await connectionAction(id, 'test');
      setVerified((values) => ({ ...values, [id]: 'Leitura validada' }));
      setStatus('Credenciais salvas e leitura da conta validada. Nenhuma ordem foi enviada.');
    } catch {
      setVerified((values) => ({ ...values, [id]: 'Falha na validação' }));
      throw new Error(
        'Credenciais salvas, mas a conexão não foi validada. Confira permissões de leitura, restrições de IP e mercado.',
      );
    }
  };
  const action = async (id: string, command: 'test' | 'activate' | 'deactivate') => {
    setVerified((values) => ({ ...values, [id]: 'Não verificada' }));
    await connectionAction(id, command);
    await load();
    setVerified((values) => ({
      ...values,
      [id]: command === 'deactivate' ? 'Desativada' : 'Leitura validada',
    }));
    setStatus(
      command === 'deactivate' ? 'Conexão desativada no aplicativo.' : 'Leitura da conta validada.',
    );
  };

  return (
    <div className="card compact-card connection-manager">
      <h2>Contas e conexões</h2>
      {/*
        ONDE A CORRETAORA É ESCOLHIDA, DE VERDADE
        ==========================================
        Antes o `select` estava DENTRO do `<fieldset disabled={busy}>` de
        criação. Bastava uma validação em voo e a troca de corretora era
        bloqueada junto — o operador ficava preso na corretora que deu erro
        de leitura, sem caminho para sair. Agora a escolha fica acima do
        fieldset: trocar corretora é sempre possível.
      */}
      <p className="muted">
        MT5 usa a sessão do terminal. Binance e MEXC usam API key e secret. Validar leitura não
        autoriza negociação.
      </p>

      {/*
        A SESSÃO DO TERMINAL, LIDA DE VERDADE.

        `account` é null até a detecção responder, e as duas coisas possíveis
        depois dela — "não há terminal aberto" e "falhou a leitura" — não podem
        virar a mesma tela vazia. Sem esta linha, o campo "Login do terminal"
        mostra "Nenhuma sessão detectada" e o operador não sabe se falta abrir
        o MT5 ou se o app que não conseguiu ler.
      */}
      {broker === 'mt5' && (
        <p className={`hint ${account ? 'con-ok' : 'con-aviso'}`}>
          {account
            ? `Sessão detectada: ${account.login} · ${account.server}.`
            : 'Nenhuma sessão do MetaTrader 5 detectada. Abra o terminal e logue na conta.'}
        </p>
      )}

      {/*
        A CONFERÊNCIA QUE VALE MAIS QUE O CAMPO.

        MEDIDO: o campo "Servidor" é o nome que VOCÊ escreve, e a sessão real
        vem do terminal. Se divergirem, a tela mentiria sobre onde a ordem vai
        sair — que é o defeito mais caro desta tela: o operador acredita na linha
        errada e a ordem vai para a outra corretora.

        Por isso a divergência é dita na tela, em vez de ser discoverta na hora
        do envio. Trocar o servidor de verdade continua sendo no terminal; aqui
        só se avisa que os dois lados estão diferentes.
      */}
      {broker === 'mt5' &&
        account &&
        server.trim() &&
        server.trim().toLowerCase() !== String(account.server || '').toLowerCase() && (
          <p className="hint con-aviso" role="status">
            A conexão está marcada como <strong>{server.trim()}</strong>, mas o terminal está
            logado em <strong>{account.server}</strong>. Troque o servidor no terminal e
            clique em Sincronizar MT5 — o app não troca de servidor sozinho.
          </p>
        )}
      <div className="order-ticket-grid">
        {/*
          A CORRETAORA NUNCA TRAVA.

          O comentário acima diz que a escolha ficou fora do `<fieldset
          disabled>` justamente para o operador poder sair da corretora que deu
          erro. Mas o `disabled={busy}` aqui desfazia isso: durante a validação
          — que é o momento exato em que se quer trocar de caminho — a troca
          ficava bloqueada. Comentário que mente sobre o próprio código é a
          forma mais cara de defeito, porque ninguém vai conferi-lo.
        */}
        <label className="field">
          Corretora
          <select value={broker} onChange={(event) => trocaBroker(event.target.value as Broker)}>
            {TODAS.map((value) => (
              <option key={value} value={value}>
                {ROTULO_BROKER[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Mercado
          <select value={market} onChange={(event) => setMarket(event.target.value)}>
            {marketsFor(broker).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

<fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
        <div className="order-ticket-grid">
          {broker === 'mt5' ? (
            <>
              {/*
                MT5 NAO TEM CAMPO DE SENHA AQUI — E ISSO E INTENCIONAL
                ==========================================================
                O `readOnly` nos dois campos de MT5 não é falha: login e
                servidor são DADOS DA SESSÃO, lidos do terminal que já está
                aberto. Digitá-los aqui não conecta nada — o app não guarda
                senha de terminal em lugar nenhum.

                O que o operador digita de verdade, quando a corretora é
                sessão, é o NOME da conexão (que é o rótulo da linha na
                tabela). Antes esse campo só existia para exchanges, e uma
                conexão de sessão ficava com nome automático vindo do
                terminal — sem forma de renomear. Agora o campo existe
                para os dois caminhos.
              */}
              <label className="field">
                Nome da conexão
                <input
                  value={name}
                  placeholder="padrão: nome e servidor do terminal"
                  onChange={(event) => setName(event.target.value)}
                />
              </label>
              {/*
                SERVIDOR — EDITÁVEL, e sem senha. (05/10/2026)

                O dono pediu: "adicionar servidores e poder trocar eles estilo
                MT5". A escolha de desenho, confirmada com ele: **vários
                servidores viram contas distintas**, e o app nunca guarda a
                senha do terminal.

                O PORQUÊ DE NÃO SER UM TROCADOR DE VERDADE
                ---------------------------------------------
                MEDIDO: o MT5 não expõe lista de servidores nem de contas.
                `account_info()` devolve só a sessão atual, e os servidores ficam
                em `accounts.dat`, cifrado. Trocar de servidor na prática exige
                **autenticar** naquela conta — login e senha do terminal.

                Então este campo é o NOME do servidor, e ele vai para o rótulo da
                conexão. É isso que permite dois servidores da mesma corretora
                como duas linhas distintas, e o operador troca pela tela de
                conexões — **a troca verdadeira acontece no terminal**, que
                é onde o login existe.

                O app continua sendo fail-closed: sem sessão do terminal
                aberta, este campo não conecta nada. Dizer o nome do servidor não
                é autenticar nele.
              */}
              <label className="field">
                Servidor
                <input
                  value={server}
                  onChange={(event) => setServer(event.target.value)}
                  placeholder={account?.server || 'ex.: XMGlobal-MT5 14'}
                  aria-label="Servidor do terminal"
                />
              </label>
              <label className="field">
                Login do terminal
                <input
                  readOnly
                  value={account?.login ?? ''}
                  placeholder="Nenhuma sessão detectada"
                />
              </label>
            </>
          ) : (
            <>
              <label className="field">
                Nome
                <input value={name} onChange={(event) => setName(event.target.value)} />
              </label>
              <label className="field">
                API key
                <input
                  type="password"
                  autoComplete="off"
                  value={key}
                  onChange={(event) => setKey(event.target.value)}
                />
              </label>
              <label className="field">
                Secret
                <input
                  type="password"
                  autoComplete="off"
                  value={secret}
                  onChange={(event) => setSecret(event.target.value)}
                />
              </label>
              {precisaPassphrase && (
                <label
                  className="field"
                  title="A OKX recusa a conexão sem a passphrase criada junto com a API key"
                >
                  <span>Passphrase</span>
                  <input
                    type="password"
                    autoComplete="off"
                    value={passphrase}
                    onChange={(event) => setPassphrase(event.target.value)}
                  />
                </label>
              )}
            </>
          )}
        </div>
        {broker !== 'mt5' && precisaPassphrase && (
          <p className="hint">
            A {ROTULO_BROKER[broker]} exige a passphrase gerada junto com a API key. Sem ela a
            corretora recusa a leitura.
          </p>
        )}
        {broker === 'mt5' && (
          <p className="hint">
            Entre na conta pelo MetaTrader 5 e deixe o terminal aberto. O aplicativo detecta a
            sessão existente, sem guardar senha, trocar contas ou controlar o EA.
          </p>
        )}
        <button
          type="button"
          className="btn primary"
          disabled={busy || pendencias.length > 0}
          onClick={() => void run(save)}
        >
          {busy ? 'Verificando…' : broker === 'mt5' ? 'Sincronizar MT5' : 'Salvar e validar API'}
        </button>

        {/*
          POR QUE O BOTÃO ESTÁ CINZA.

          A lista é o que transforma um botão morto em uma instrução. Antes o
          operador via o botão apagado e não tinha como saber o que faltava —
          e no MT5 o que faltava era um NOME que nem era obrigatório.
        */}
        {pendencias.length > 0 && (
          <ul className="hint con-pendencias">
            {pendencias.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        {/*
          Botão desabilitado sem nome é melhor do que erro depois do clique:
          `saveExchange` recusa conexão sem nome, e a recusa chegava como
          exceção em vez de o campo simplesmente não estar pronto.
        */}
      </fieldset>
      <p role="status" aria-live="polite">
        {status}
      </p>
      <div className="table-scroll">
        <table className="tbl compact-table">
          <thead>
            <tr>
              <th>Conexão</th>
              <th>Corretora</th>
              <th>Mercado</th>
              <th>Estado</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.id.split(':').slice(2).join(':')}</td>
                <td>{row.broker.toUpperCase()}</td>
                <td>{row.market}</td>
                <td>
                  {row.active === false
                    ? 'Desativada'
                    : (verified[row.id] ?? 'Salva · não verificada')}
                </td>
                <td>
                  <div className="conexao-acoes">
                  <button
                    disabled={busy}
                    className="btn xs ghost"
                    onClick={() => void run(() => action(row.id, 'test'))}
                  >
                    Testar leitura
                  </button>
                  <EditarConexao linha={row} aoTerminar={load} />
                  <button
                    disabled={busy}
                    className="btn xs ghost"
                    onClick={() =>
                      void run(() =>
                        action(row.id, row.active === false ? 'activate' : 'deactivate'),
                      )
                    }
                  >
                    {row.active === false ? 'Ativar' : 'Desativar'}
                  </button>
                  <button
                    disabled={busy}
                    className="btn xs danger"
                    onClick={() => {
                      if (!window.confirm('Excluir as credenciais desta conexão do aplicativo?'))
                        return;
                      void run(async () => {
                        await requestConnection(
                          `/api/connections/${encodeURIComponent(row.id)}`,
                          'DELETE',
                        );
                        await load();
                        setStatus('Conexão excluída.');
                      });
                    }}
                  >
                    Excluir conexão
                  </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
