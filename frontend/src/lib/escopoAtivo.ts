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
 * Le a conta ativa. Se nao houver nada gravado, assume MT5/forex — que e o
 * mercado do produto. Nao ha fallback por componente.
 */
export function escopoAtivo(): EscopoAtivo {
  let stored = '';
  try {
    stored = window.localStorage.getItem(CHAVE_CONTA_ATIVA) || '';
  } catch {
    stored = '';
  }
  const [broker, market] = stored.split(':');
  const brokerId = broker || 'mt5';
  return {
    broker: brokerId,
    market: compatibleMarket(brokerId, market || 'forex') || 'forex',
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
