// Trocar a credencial de uma conexão que já existe.
//
// POR QUE ISTO EXISTE (05/10/2026)
// ================================
// A tela de contas e conexões só sabia CRIAR. O campo de chave ficava vazio
// depois de salvar (a tela limpava o estado), e a listagem nunca devolve a
// chave de volta — o que é correto, não vaza segredo. Resultado: o operador
// via um campo que não dá para preencher de novo e um botão só de excluir.
//
// Modificar significava excluir a conexão e cadastrar outra com o mesmo nome.
// No meio, a conta ficava sem credencial, e se o cadastro novo falhasse o
// cliente ficava sem chave nenhuma.
//
// Aqui editar preenche os campos vazios com o que já está gravado e manda o
// PUT. O usuário nunca precisa ver a chave atual para poder trocar outra.

import { useState } from 'react';
import {
  connectionAction,
  marketsFor,
  requestConnection,
  ROTULO_BROKER,
  type Broker,
  type Connection,
} from '../lib/connections';

type Props = {
  linha: Connection;
  aoTerminar: () => void | Promise<void>;
};

/**
 * `@param linha` — a conexão da tabela. Vem de `/api/connections`, que NUNCA
 * devolve credencial: só `id`, `broker`, `market`, `configured`, `active` e
 * `credential_source`.
 */
export default function EditarConexao({ linha, aoTerminar }: Props) {
  const [aberto, setAberto] = useState(false);
  const [key, setKey] = useState('');
  const [secret, setSecret] = useState('');
  const [passphrase, setPassphrase] = useState('');
  const [mercado, setMercado] = useState(linha.market);
  const [ocupado, setOcupado] = useState(false);
  const [status, setStatus] = useState('');

  const broker = linha.broker as Broker;
  const opcoes = marketsFor(broker);
  const porSessao = linha.credential_source === 'session';

  const limpar = () => {
    setKey('');
    setSecret('');
    setPassphrase('');
    setStatus('');
  };

  const salvar = async () => {
    if (ocupado) return;
    setOcupado(true);
    setStatus('Gravando…');
    try {
      // O `id` da conexao ja carrega `broker:market:nome`. O nome vem do
      // proprio id para que a edicao nunca crie uma conexao paralela por
      // engano de digitacao.
      await requestConnection(`/api/connections/${encodeURIComponent(linha.id)}`, 'PUT', {
        id: linha.id,
        broker,
        market: mercado,
        ...(key.trim() ? { api_key: key.trim() } : {}),
        ...(secret.trim() ? { api_secret: secret.trim() } : {}),
        ...(passphrase.trim() ? { api_passphrase: passphrase.trim() } : {}),
      });
      await aoTerminar();
      // Validar a leitura depois de gravar e o que da a certeza de que a
      // credencial nova funciona — gravar e conseguir ler sao coisas
      // diferentes, e a tela prometia a segunda quando clicava em "Salvar".
      await connectionAction(linha.id, 'test');
      await aoTerminar();
      setAberto(false);
      limpar();
      setStatus('Credencial atualizada e leitura validada. Nenhuma ordem foi enviada.');
    } catch (error) {
      const mensagem = error instanceof Error ? error.message : 'Falha ao atualizar.';
      // A credencial pode ter ficado gravada e só a LEITURA ter falhado.
      // Dizer "não salvou" seria falso e levaria o operador a gravar de novo
      // por cima de uma credencial que já está no lugar.
      setStatus(
        `${mensagem} A credencial pode ter sido gravada; a leitura é que não foi confirmada.`,
      );
    } finally {
      setOcupado(false);
    }
  };

  const cancelar = async () => {
    setAberto(false);
    limpar();
    await aoTerminar();
  };

  if (!aberto) {
    return (
      <button
        type="button"
        className="btn xs ghost"
        disabled={ocupado}
        onClick={() => setAberto(true)}
      >
        Trocar chave
      </button>
    );
  }

  return (
    <div className="conexao-edicao">
      <div className="order-ticket-grid conexao-edicao-grade">
        <label className="field">
          Mercado
          <select value={mercado} onChange={(event) => setMercado(event.target.value)}>
            {opcoes.map((valor) => (
              <option key={valor} value={valor}>
                {valor}
              </option>
            ))}
          </select>
        </label>
        {porSessao ? (
          <p className="hint conexao-edicao-sessao">
            {ROTULO_BROKER[broker]} usa a sessão do terminal: aqui só muda o mercado. Para trocar a
            conta, entre pelo próprio terminal.
          </p>
        ) : (
          <>
            <label className="field">
              Nova API key
              <input
                type="password"
                autoComplete="off"
                value={key}
                placeholder="em branco = manter a atual"
                onChange={(event) => setKey(event.target.value)}
              />
            </label>
            <label className="field">
              Novo secret
              <input
                type="password"
                autoComplete="off"
                value={secret}
                placeholder="em branco = manter o atual"
                onChange={(event) => setSecret(event.target.value)}
              />
            </label>
          </>
        )}
      </div>
      <p className="hint">
        Campo em branco mantém o que já está gravado — a chave atual nunca é lida de volta para a
        tela.
      </p>
      {status && (
        <p role="status" aria-live="polite">
          {status}
        </p>
      )}
      <div className="btn-row">
        <button
          type="button"
          className="btn xs primary"
          disabled={ocupado}
          onClick={() => void salvar()}
        >
          {ocupado ? 'Gravando…' : 'Gravar e validar'}
        </button>
        <button
          type="button"
          className="btn xs ghost"
          disabled={ocupado}
          onClick={() => void cancelar()}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}