/*
  O VALOR DO NIVEL — SL E TP EM DINHEIRO (05/10/2026)
  ====================================================
  MEDIDO NA PROPRIA TELHA, e nao em comentario: o campo "Valor no risco (SL)"
  calculava `preco * lote * distancia`. Com os numeros da captura XM
  (BTCUSD 85.865,35 · lote 0,01 · distancia 8,45) isso dava:

      tela   : 7.255,62 USD
      real   :     0,08 USD

  Um exagero de 85.865x — que e exatamente o PRECO, porque a formula multiplica
  pelo preco em vez de multiplicar pela DISTANCIA ate o nivel. Numa conta de
  13,25 USD a tela afirmava risco de 7.255 USD. E `contract_size`, que a
  corretora entrega, nunca era lido.

  A conta certa e a distancia entre o nivel e a entrada, vezes o volume, vezes o
  tamanho do contrato:

      dinheiro = |entrada - nivel| * volume * contract_size

  `contract_size` e o que separa crypto de forex: em BTCUSD e 1 (um token), em
  EURUSD e 100.000. Sem ele, "lote" nao significa nada de dinheiro.

  SEM CONTRATO, NAO HÁ NUMERO
  ----------------------------
  Se a corretora nao devolveu `contract_size`, esta funcao devolve `null` e a
  tela escreve "depende do contrato" em vez de um numero. Numero de risco
  inventado e o pior defeito que uma tela de operacao pode ter: o operador
  dimensiona a posicao por ele.
*/

export type Lado = 'compra' | 'venda';

/*
  SO O CONTRATO IMPORTA aqui. `point` e `digits` entram no nivel ja arredondado
  pela tela; o valor em dinheiro depende apenas de `contract_size`.
*/
export type Ficha = { contractSize?: number | null } | null | undefined;

/** O contrato e utilizavel? Zero, negativo e ausente nao sao. */
export function contratoUtilizavel(ficha: Ficha): number | null {
  const c = ficha?.contractSize;
  return typeof c === 'number' && Number.isFinite(c) && c > 0 ? c : null;
}

/**
 * Dinheiro em jogo entre a entrada e o nivel. `null` quando nao ha contrato.
 *
 * O sinal do lado nao entra: o valor e um VALOR ABSOLUTO. `-2.00 USD` de stop e
 * `2.00 USD` de alvo tem o mesmo tamanho, e a tela mostra o SL negativo e o TP
 * positivo por conta propria.
 */
export function valorDoNivel(
  entrada: number,
  nivel: number,
  volume: number,
  ficha: Ficha,
): number | null {
  const contrato = contratoUtilizavel(ficha);
  if (contrato === null) return null;
  if (!Number.isFinite(entrada) || !Number.isFinite(nivel)) return null;
  if (!Number.isFinite(volume) || volume <= 0) return null;
  return Math.abs(entrada - nivel) * volume * contrato;
}

/**
 * O NIVEL que produz o dinheiro pedido, seguindo o preco.
 *
 * E o que o dono pediu: o operador determina o VALOR, e o nivel se recalcula
 * para que o valor continue sendo esse enquanto o preco anda.
 *
 * `entrada` e de proposito um PARAMETRO, e nao o preco atual. Ate a posicao
 * abrir, o que ancora o valor e o preco de entrada previsto; depois de aberta,
 * e o preco de entrada real. Passar o preco atual aqui seria mudar a
 * ancora a cada tick e fazer o valor deslizar junto com o preco — que e o
 * oposto de "manter o valor".
 */
export function nivelParaValor(
  entrada: number,
  valor: number,
  volume: number,
  lado: Lado,
  ficha: Ficha,
): number | null {
  const contrato = contratoUtilizavel(ficha);
  if (contrato === null) return null;
  if (!Number.isFinite(entrada) || !Number.isFinite(valor)) return null;
  if (!Number.isFinite(volume) || volume <= 0) return null;
  if (valor <= 0) return null;
  const distancia = valor / (volume * contrato);
  return lado === 'compra' ? entrada + distancia : entrada - distancia;
}

/** O dinheiro como a TELA escreve: SL negativo, TP positivo. */
export function valorComSinal(valor: number | null, lado: Lado): number | null {
  if (valor === null) return null;
  return lado === 'venda' ? -valor : valor;
}

/** Texto honesto quando o numero nao existe. */
export const SEM_CONTRATO = 'depende do contrato';

export default valorDoNivel;