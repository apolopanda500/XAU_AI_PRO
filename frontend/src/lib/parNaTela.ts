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

/**
 * O NOME DE UM MODELO NAO E UM PAR (12/11/2026)
 * =============================================
 * MEDIDO no app INSTALADO 1.2.182 (12/11 23:50), aba ROBO, texto lido da tela:
 *
 *   Gráfico indisponível: nenhuma fonte publica respondeu para MULTI_METALS M5
 *   (binance: sem equivalente para este par ou perodo; yahoo: ...;
 *    frankfurter: ...)
 *
 * O par consultado era `MULTI_METALS` — o NOME DO MODELO de classe, e nao um
 * ativo. Ele chegou ali por `ListaModelos.escolher`, que gravava `m.symbol`, e
 * nos artefatos `MULTI_*` o `symbol` do `meta.json` E o proprio nome do modelo.
 *
 * O backend ja recusa esse nome como ativo. Medido agora, no Python do repo:
 *
 *   simbolo_valido('MULTI_METALS')    -> False
 *   classe_de('MULTI_METALS')         -> OUTROS
 *   _tentativas_multi('MULTI_METALS') -> []
 *   classe_de('XAUUSD')               -> METALS
 *   _tentativas_multi('XAUUSD','M5')  -> [('MULTI_METALS','MULTI_METALS_M5'), ...]
 *
 * A ultima linha e o que resolve o caso sem adivinhar ativo: o modelo de
 * CLASSE entra sozinho para o ativo REAL (`_classe_multi_de` -> classe do
 * simbolo). Usado como par, o nome do modelo nao produz candle nem inferencia.
 * Quem aceitava `MULTI_METALS` como par era a TELA — este arquivo.
 */
export function ehClasseDeModelo(valor: string | null | undefined): boolean {
  return /^MULTI_[A-Z0-9_]+$/.test(String(valor ?? '').trim().toUpperCase());
}

/** Um par de verdade: texto nao vazio que nao seja nome de modelo de classe. */
function parDeVerdade(valor: string | null | undefined): string {
  const texto = String(valor ?? '').trim().toUpperCase();
  return ehClasseDeModelo(texto) ? '' : texto;
}

export function parNaTela(auto: ParDoMotor | null | undefined, escolhido: string | null | undefined): string {
  const doMotor = parDeVerdade(auto?.simbolo);
  const daTela = parDeVerdade(escolhido);
  const ligado = Boolean(auto?.ativo);
  return ligado ? doMotor || daTela : daTela || doMotor;
}
