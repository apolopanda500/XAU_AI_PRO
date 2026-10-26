/**
 * O par que a TELA mostra — uma regra, tres leitores.
 *
 * MEDIDO no app instalado (22/10/2026): a barra inferior dizia `BTCUSD`, o
 * seletor "Par para operar" dizia `XAUUSD` e o grafico desenhava `XAUUSD`
 * embaixo de um cabecalho que dizia `BTCUSD`. Tres paineis, o mesmo dado, tres
 * respostas — porque cada um tinha a sua propria precedencia entre `auto.simbolo`
 * (o par GRAVADO no motor) e `selectedSymbol` (a escolha do operador):
 *
 *   OperacaoAutomatica.tsx:223   auto?.simbolo || parEscolhido
 *   StatusBar.tsx:99             autoQ.data?.simbolo || selectedSymbol
 *   AcompanharModelos.tsx:84     auto?.simbolo || parDaTela
 *
 * A regra e uma so, e ela nao escolhe "melhor" entre dois valores guardados:
 *
 *   MOTOR LIGADO   -> o par do motor, porque e o que ele esta operando de
 *                     verdade. Mostrar a escolha da tela aqui seria dizer que
 *                     ele opera um par que ele nao opera.
 *   MOTOR DESLIGADO-> a escolha da tela, porque o par do motor e um valor
 *                     antigo que ninguem esta usando. Deixar ele vencer era o
 *                     defeito: o operador trocava o par e a tela continuava no
 *                     anterior.
 *
 * Vazio continua vazio (AGENTS.md §3): sem escolha e sem motor, `''` — recusa
 * com motivo, nunca um ativo padrao.
 */
export interface ParDoMotor {
  simbolo?: string | null;
  ativo?: boolean | null;
}

export function parNaTela(auto: ParDoMotor | null | undefined, escolhido: string | null | undefined): string {
  const doMotor = String(auto?.simbolo ?? '').trim().toUpperCase();
  const daTela = String(escolhido ?? '').trim().toUpperCase();
  const ligado = Boolean(auto?.ativo);
  return ligado ? doMotor || daTela : daTela || doMotor;
}
