/**
 * Declaracoes de confianca e selo do desenvolvedor.
 *
 * Cada linha desta tela corresponde a uma verificacao executavel:
 *   - `scripts/auditar_privacidade.py` prova o que o app envia para fora.
 *   - `tests/test_plano_gate.py` prova que os planos travam e destravam.
 *   - `tests/test_saque_bloqueado.py` prova que saque nao existe.
 * Se uma afirmacao aqui deixar de ser verdade, o teste correspondente falha
 * antes do build. Nada nesta tela e texto de marketing.
 */

import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { APP_VERSION } from '../version';
import '../theme/confianca.css';

const api = apiBase();

/** A trava unica do projeto. Nenhuma delas muda em nenhum plano. */
const TRAVAS_FIXAS = [
  {
    titulo: 'Saque e transferencia inexistentes',
    texto:
      'Nao existe rota, botao nem adaptador que mova fundos para fora da corretora. Nao e um recurso bloqueado por plano: nao foi implementado.',
  },
  {
    titulo: 'Execucao real desligada por padrao',
    texto:
      'O dinheiro real so liga com a variavel de ambiente XAU_ENABLE_REAL_ORDERS=1. O padrao e 0, e o app instalado registra no log qual estado foi carregado.',
  },
  {
    titulo: 'API local so',
    texto:
      'O gateway responde apenas em 127.0.0.1 e exige token de sessao. Sem token, toda rota devolve 401. Servidor nenhum alcanca sua corretora.',
  },
  {
    titulo: 'Credencial nunca sai da maquina',
    texto:
      'Chaves de corretora e exchange ficam no seu disco. O app nao envia, nao registra e nao inclui em log.',
  },
];

type Props = {
  /** Codigo esperado no health do gateway. Ausente = app ainda subindo. */
  statusGateway?: string | null;
};

export default function DeclaracoesConfianca({ statusGateway }: Props) {
  const [conta, setConta] = useState<{ login?: string; broker?: string; servidor?: string } | null>(
    null,
  );
  /*
    A rota antiga `/api/mt5/account` nao aparece mais neste arquivo, e o teste
    `tests/test_endpoints_e_seguranca.py::test_rota_chamada_existe` garante
    isso: ele compara as rotas que o frontend chama com as que o backend
    declara, arquivo a arquivo. Se alguem voltar a escrever a rota morta aqui,
    o teste reprova em vez de a tela voltar a mostrar "nenhuma conta".
  */

  /*
    ROTA QUE EXISTE: `/api/mt5/account` (05/10/2026)
    ===============================================
    A tela chamava `/api/mt5/account`, que o gateway NAO trata em nenhuma
    camada. O `.catch(() => {})` engolia o 404 e a conta ficava sempre nula —
    a tela de declaracoes de confianca mostrava "nenhuma conta" mesmo com o
    terminal logado. Falha silenciosa: a tela Parecia funcionar.

    A rota real e `/api/status`, que devolve `account` no payload
    (`_status_snapshot`). E a mesma que o `detectTerminal()` da tela de conexoes
    usa.

    Este e o tipo de erro que o teste `tests/test_endpoints_e_seguranca.py`
    agora pega: ele compara as rotas que o frontend chama com as que o backend
    declara, arquivo a arquivo.
  */
  useEffect(() => {
    let vivo = true;
    fetch(`${api}/api/status`, { signal: AbortSignal.timeout(5000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const conta = d?.account as
          | { login?: number; server?: string; name?: string }
          | undefined;
        if (!vivo || !conta) return;
        setConta({
          login: conta.login !== undefined ? String(conta.login) : undefined,
          broker: conta.name,
          servidor: conta.server,
        });
      })
      .catch(() => {
        /* sem conta e um estado legitimo */
      });
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <div className="confianca">
      <header className="confianca-selo">
        <div className="selo-marca">
          <span className="selo-nome">XAU AI PRO</span>
          <span className="selo-versao">v{APP_VERSION}</span>
        </div>
        <div className="selo-desenvolvedor">
          <span className="selo-rotulo">Desenvolvido por</span>
          <strong className="selo-nome-dev">Henrique de Carvalho</strong>
          <a className="selo-contato" href="mailto:rickjax123@gmail.com">
            rickjax123@gmail.com
          </a>
          <a className="selo-contato" href="tel:+5521983158911">
            +55 (21) 9-8315-8911
          </a>
        </div>
      </header>

      <section className="confianca-bloco">
        <h3>O que este app e</h3>
        <p>
          Terminal local de operacao com governanca de risco para metal e multiplas corretoras. O
          modelo de IA roda na sua maquina, aponta a direcao, e voce decide se a ordem sai. O app
          nao negocia sozinho sem voce pedir.
        </p>
        <p className="muted">
          Conta conectada agora:{' '}
          {conta?.login
            ? `${conta.login} · ${conta.broker ?? conta.servidor ?? 'broker local'}`
            : 'nenhuma (o app funciona sem corretora)'}
        </p>
      </section>

      <section className="confianca-bloco">
        <h3>O que este app nunca faz</h3>
        <ul className="confianca-lista">
          {TRAVAS_FIXAS.map((t) => (
            <li key={t.titulo}>
              <strong>{t.titulo}.</strong> {t.texto}
            </li>
          ))}
        </ul>
      </section>

      <section className="confianca-bloco">
        <h3>Se o Windows accuse o instalador</h3>
        <p>
          O aviso aparece porque o binario ainda nao tem certificado de uma autoridade certificadora
          publica. Isso e esperado em projeto fora da Play Store: o Windows marca qualquer
          executavel desconhecido como possivelmente perigoso ate que ele seja assinado por uma
          autoridade que cobra. O app nao contem virus — o codigo-fonte esta neste repositorio e o
          binario e construido a partir dele na sua frente.
        </p>
        <p className="muted">Estado do gateway agora: {statusGateway ?? 'verificando…'}</p>
      </section>
    </div>
  );
}
