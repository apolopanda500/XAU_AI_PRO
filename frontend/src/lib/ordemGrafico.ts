/**
 * A ORDEN ARMADA: preco, stop e alvo em DINHEIRO, e o que a linha mostra.
 *
 * MEDIDO NAS CAPTURAS DA XM (06/10/2026)
 * =======================================
 * `C:\Users\Micro\Pictures\Screenshots\Screenshot 2026-10-06 141239.png` e
 * `...141407.png`, conta Real 11,47, BTCUSD. O que a XM escreve nas linhas:
 *
 *     captura 141239:   0,01 | −2,00 USD | ×     em 85.694,50
 *                       0,01 | +2,00 USD | ×     em 85.305,49
 *     captura 141407:   0,01 | −1,50 USD | ×     em 85.663,29
 *                       0,01 | +1,52 USD | ×     em 85.361,80
 *
 * DUAS COISAS QUE A CAPTURA ENSINA E QUE O CODIGO NAO SABIA
 * =========================================================
 *
 * 1. O STOP E O ALVO SAO ESCOLHIDOS EM DINHEIRO. O operador escreve "quanto
 *    aceito perder" e o PRECO da linha e derivado. `−2,00 USD` e `+2,00 USD` na
 *    primeira captura sao simetricos por PADRAO — a XM comeca em 1:1.
 *
 * 2. O PRECO CLICADO E O PONTO DE PARTIDA, E O SL/TP FICAM DOS DOIS LADOS.
 *    Com entrada em 85.510,25 e `−2,00 USD`, o stop fica ACIMA (85.694,50) e o
 *    alvo ABAIXO (85.305,49) — o que so faz sentido para uma VENDA. Para uma
 *    compra o stop fica abaixo. O LADO e do operador, e o nivel respeita o lado.
 *
 * A REGRA DO NIVEL
 * =================
 *     nivel = entrada -/+ dinheiro / (volume * contract_size)
 *
 * O `contract_size` e o que separa crypto de forex: 1 em BTCUSD, 100.000 em
 * EURUSD. SEM ELE nao existe conversao, e o nivel sai 100.000 vezes errado — e
 * um stop errado manda ordem errada. Por isso `null` e RECUSA, nunca estimativa.
 */

/** O que o operador pode definir: em dinheiro (padrao da XM) ou em preco. */
export type ModoProtecao = 'dinheiro' | 'preco';

/** Uma ordem armada pelo clique. Ainda nao enviada. */
export type OrdemArmada = {
  /** Preco que o operador clicou, ja convertido para preco pela ficha. */
  entrada: number;
  lado: 'BUY' | 'SELL';
  volume: number;
  /** `contract_size` do ativo, da ficha da corretora. `null` recusa. */
  contrato: number | null;
  /** Quanto o operador aceita perder. `null` quando o modo e `preco`. */
  riscoValor: number | null;
  /** Quanto o operador espera ganhar. `null` quando o modo e `preco`. */
  alvoValor: number | null;
  /** Stop em PRECO. `null` quando o modo e `dinheiro`. */
  slPreco: number | null;
  /** Alvo em PRECO. `null` quando o modo e `dinheiro`. */
  tpPreco: number | null;
};

/** Por que o nivel nao pode ser calculado. O texto e o que o operador le. */
export type Motivo =
  | { ok: true }
  | { ok: false; motivo: string };

/**
 * As tres LINHAS que a XM desenha, com o texto que ela escreve.
 *
 * O `papel` e o que a CORRETORA e o motor entendem. O `cor` e o que o operador
 * distingue de relance: laranja para o stop, verde para o alvo, vermelho para a
 * posicao aberta.
 */
export type LinhaOrdem = {
  papel: 'entrada' | 'sl' | 'tp';
  preco: number;
  /** `0,01 | −2,00 USD` — o que a XM escreve, na ordem dela. */
  rotulo: string;
  cor: string;
};

/**
 * O volume da ordem ARMADA, como o operador o digitou.
 *
 * SEM sinal. MEDIDO: a linha da entrada armada na XM escreve `0,01 | −2,00 USD`
 * — o volume sem sinal, e o dinheiro com sinal. O sinal negativo que a captura
 * mostra (`−0,01 | −0,37 USD`) e da POSICAO que ja estava aberta, que e uma
 * linha diferente e vermelha.
 */
const volumeDaOrdem = (volume: number, casas = 2): string =>
  Math.abs(volume).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });

/**
 * O volume como a XM escreve: com o sinal do LADO da posicao.
 *
 * MEDIDO: a posicao ABERTA aparece como `−0,01` e e uma VENDA — `+0,01` seria
 * uma posicao comprada, e o sinal e o que diz ao operador o lado em que ele
 * esta-perdendo. Por isso esta funcao e separada de `volumeDaOrdem`, que e a
 * ordem ARMADA: uma ordem nova mostra o volume como digitado.
 */
export function volumeComSinalDaPosicao(volume: number, lado: 'BUY' | 'SELL', casas = 2): string {
  const n = Math.abs(volume).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  });
  return `${lado === 'SELL' ? '−' : '+'}${n}`;
}

/** `−2,00 USD` / `+1,52 USD`, no formato pt-BR da XM. */
const dinheiro = (valor: number, casas = 2): string => {
  const sinal = valor < 0 ? '−' : '+';
  return `${sinal}${Math.abs(valor).toLocaleString('pt-BR', {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  })} USD`;
};

/**
 * O NIVEL de um valor em dinheiro, no preco.
 *
 *     |nivel - entrada| = dinheiro / (volume * contract_size)
 *
 * O sinal do nivel depende do PAPEL, e nao do valor: o stop fica do lado que
 * PERDE, o alvo do lado que GANHA. E o LADO da ordem que diz qual e cada um.
 */
export function nivelDoValor(
  entrada: number,
  valor: number,
  volume: number,
  lado: 'BUY' | 'SELL',
  contrato: number | null,
  papel: 'stop' | 'alvo',
): number | null {
  if (contrato === null) return null;
  if (!Number.isFinite(entrada) || entrada <= 0) return null;
  if (!Number.isFinite(valor) || valor <= 0) return null;
  if (!Number.isFinite(volume) || volume <= 0) return null;
  if (!Number.isFinite(contrato) || contrato <= 0) return null;
  const distancia = valor / (volume * contrato);
  // Stop: sempre do lado que perde. Compra perde para baixo; venda perde para
  // cima. Alvo: o oposto. E por isso que o MESMO dinheiro produz dois niveis
  // em lados opostos, e nao um so.
  const paraCima = papel === 'stop' ? lado === 'SELL' : lado === 'BUY';
  return paraCima ? entrada + distancia : entrada - distancia;
}

/**
 * AS TRES LINHAS da XM, com o rotulo que ela escreve.
 *
 * Devolve lista vazia quando falta o que a conta nao tem: sem `contract_size`
 * nao existe nivel em dinheiro, e escrever um nivel estimado seria o app
 * inventando onde a ordem para.
 */
export function linhasDaOrdem(ordem: OrdemArmada): LinhaOrdem[] {
  const linhas: LinhaOrdem[] = [
    {
      papel: 'entrada',
      preco: ordem.entrada,
      rotulo: `${volumeDaOrdem(ordem.volume)} | ${dinheiro(ordem.lado === 'SELL' ? -(ordem.riscoValor ?? 0) : ordem.riscoValor ?? 0)}`,
      cor: 'rgba(139,147,167,.9)',
    },
  ];
  if (ordem.slPreco !== null) {
    linhas.push({
      papel: 'sl',
      preco: ordem.slPreco,
      rotulo: `${volumeDaOrdem(ordem.volume)} | ${dinheiro(-(ordem.riscoValor ?? 0))}`,
      cor: '#e8a33d',
    });
  }
  if (ordem.tpPreco !== null) {
    linhas.push({
      papel: 'tp',
      preco: ordem.tpPreco,
      rotulo: `${volumeDaOrdem(ordem.volume)} | ${dinheiro(ordem.alvoValor ?? 0)}`,
      cor: '#2ecc71',
    });
  }
  return linhas;
}

/**
 * O que a XM escreveria no botao: `Colocar ordem a 85.510,25`.
 *
 * O preco vai no BOTAO e nao so na linha: o operador le o preco que vai ser
 * enviado no lugar onde decide enviar.
 */
export const rotuloDoBotao = (preco: number): string =>
  `Colocar ordem a ${preco.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
