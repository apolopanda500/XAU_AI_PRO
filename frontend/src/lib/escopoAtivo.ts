/**
 * Escopo de corretora/mercado ativo.
 *
 * ANTES: `xau-active-account` era lido em dois lugares com defaults
 * diferentes — RobotCommandActions assumia 'forex' e UniversalLiveTerminal usava
 * compatibleMarket(...). Se a chave nao existisse, os dois paineis discordavam
 * sobre qual mercado estava ativo, e o mesmo ativo podia ser interpretado em
 * mercados diferentes dependendo de onde o usuario clicasse.
 *
 * AGORA: uma funcao, um default, um lugar.
 */
import { compatibleMarket } from './brokerCatalog';

export const CHAVE_CONTA_ATIVA = 'xau-active-account';

/**
 * O ID da conexao escolhida, em CHAVE SEPARADA (22/10/2026).
 *
 * MEDIDO: `xau-active-account` guarda `broker:market` — o ROTULO do par — e o
 * ID da conexao se perdia na ativacao. Com duas contas MT5 ativas no mesmo
 * terminal (real e demo), o motor recusava com "account_id e obrigatorio
 * quando ha mais de uma conta ativa": a recusa era correta, mas nao existia
 * jeito de fazer a escolha, porque o painel nao tinha de onde pegar o ID.
 *
 * CHAVE SEPARADA de proposito: `xau-active-account` tem formato assertado em
 * testes (`'mt5:metals'`) e e lido por oito componentes. Mexer nele mudaria um
 * contrato ja travado para ganhar um campo. Aqui o ID anda ao lado.
 */
export const CHAVE_CONTA_ID = 'xau-active-account-id';

/** O ID da conexao escolhida, ou '' quando o operador nao escolheu uma. */
export function contaAtivaId(): string {
  try {
    return (window.localStorage.getItem(CHAVE_CONTA_ID) || '').trim();
  } catch {
    return '';
  }
}

export interface EscopoAtivo {
  broker: string;
  market: string;
}

/**
 * Le a conta ativa.
 *
 * SEM CONTA GRAVADA, SEM ESCOPO (11/10/2026, decisao do dono: nada de MT5
 * fixo).
 * ===========================================================
 * Antes esta funcao devolvia `mt5:forex` quando a chave nao estava gravada —
 * "o mercado do produto". Na pratica, a aba ROBO inteira nascia falando MT5:
 * o cabecalho da operacao automatica, a fonte do grafico, o catalogo do
 * seletor de modelo e a faixa de mercado — tudo antes de o operador escolher
 * qualquer corretora. E o AGENTS.md §3 pelo outro lado: nenhuma corretora
 * pode ser o caminho presumido, e simbolo/corretora vazios sao RECUSA COM
 * MOTIVO, nunca um padrao silencioso.
 *
 * Agora: sem chave, `{ broker: '', market: '' }`. Quem le trata vazio como
 * "escolha a corretora/conta" — a faixa mostra `sem corretora`, o grafico
 * nao consulta, o seletor nao lista, e o ligar recusa nomeando a barra
 * inferior. Nao ha fallback por componente: o unico `|| 'mt5'` que existia
 * nos leitores saiu junto.
 */
export function escopoAtivo(): EscopoAtivo {
  let stored = '';
  try {
    stored = window.localStorage.getItem(CHAVE_CONTA_ATIVA) || '';
  } catch {
    stored = '';
  }
  const [broker, market] = stored.split(':');
  const brokerId = (broker || '').trim().toLowerCase();
  if (!brokerId) return { broker: '', market: '' };
  return {
    broker: brokerId,
    market: compatibleMarket(brokerId, (market || '').trim().toLowerCase() || 'forex') || '',
  };
}

/**
 * Grava a conta ativa. Usado pelos paineis de conexao.
 *
 * O `contaId` e OPCIONAL e vem do ID da conexao que o operador acabou de
 * ativar. Sem ele a chave de ID e APAGADA — de proposito: um ID velho de uma
 * conexao anterior nunca pode sobreviver a uma nova escolha sem ID. O pior
 * resultado possivel aqui seria o motor operando a conta ERRADA em silencio;
 * sem ID o motor cai na resolucao unica (e recusa com motivo se houver duas).
 */
export function definirEscopoAtivo(broker: string, market: string, contaId?: string): void {
  try {
    window.localStorage.setItem(CHAVE_CONTA_ATIVA, `${broker}:${market}`);
    const id = (contaId || '').trim();
    if (id) {
      window.localStorage.setItem(CHAVE_CONTA_ID, id);
    } else {
      window.localStorage.removeItem(CHAVE_CONTA_ID);
    }
  } catch {
    // localStorage indisponivel (modo privado). O app segue com o default.
  }
}

/**
 * Apaga a conta ativa. Usado ao DESATIVAR a conexao que estava escolhida:
 * sem isso a ROBO continuaria falando da corretora que o operador acabou de
 * desligar — o mesmo defeito do default fixo, so que gravado pela propria
 * mao dele.
 */
export function limparEscopoAtivo(): void {
  try {
    window.localStorage.removeItem(CHAVE_CONTA_ATIVA);
    // O ID anda junto: apagar a escolha sem apagar o ID deixaria um
    // account_id orfao que o proximo motor leria como escolha valida.
    window.localStorage.removeItem(CHAVE_CONTA_ID);
  } catch {
    // Sem chave, sem escopo: o estado final e o mesmo.
  }
}
