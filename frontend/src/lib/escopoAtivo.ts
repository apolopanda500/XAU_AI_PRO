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

/** Grava a conta ativa. Usado pelos paineis de conexao. */
export function definirEscopoAtivo(broker: string, market: string): void {
  try {
    window.localStorage.setItem(CHAVE_CONTA_ATIVA, `${broker}:${market}`);
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
  } catch {
    // Sem chave, sem escopo: o estado final e o mesmo.
  }
}
