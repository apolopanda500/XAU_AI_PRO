// XAU_AI_PRO v1.2.65
#ifndef SYMBOLVALIDATOR_MQH
#define SYMBOLVALIDATOR_MQH


#include "Config.mqh"

//==================================================
// INIT
//==================================================

void InitSymbolValidator()
{
   // reservado para futuras regras
}



//==================================================
// VALIDAÇÃO DE EXECUÇÃO REAL
//==================================================
// v1.2.65 (P1.51). MEDIDO em 02/11/2026 sobre 104 ficheiros .mq5/.mqh:
// esta função tinha 1 definição e ZERO chamadas - era código morto desde a
// v1.2.9. Nesse tempo a entrada nunca perguntou ao símbolo:
//   - se estava sincronizado (lacuna #1 da §45: SymbolIsSynchronized não
//     aparecia em ficheiro nenhum do EA);
//   - se a sessão aceitava ordens (SYMBOL_TRADE_MODE);
//   - se ask/bid eram cotações reais e não lixo de uma sessão antiga.
// O lote já era validado inline no CalculateDynamicLot, mas por ausência de
// chamada nada disto chegava ao caminho de entrada: o broker recusava e o
// journal só dizia "erro de broker".
//
// O spread NÃO se repete aqui de propósito: Filters\SpreadFilter.mqh:91 já
// fecha a entrada com a mesma GetMaxSpread(symbol). Duplicar o critério num
// portão fail-closed só acrescentaria formas de bloquear por engano.
//
// Devolve o motivo em `reason` para a recusa ser diagnosticável.

bool ValidateSymbol(
   const string symbol,
   double lot,
   double slPoints,
   string &reason
)
{
   reason = "";

   if(symbol == "")
   {
      reason = "simbolo vazio";
      return false;
   }

   // v1.2.65: SymbolIsSynchronized devolve false enquanto o terminal ainda
   // está a receber a história do servidor. Nesse instante ask/bid podem ser
   // da sessão anterior e o lote é calculado sobre um preço que já não existe.
   if(!SymbolInfoInteger(symbol, SYMBOL_SELECT))
   {
      reason = "simbolo fora do Market Watch";
      return false;
   }

   if(!SymbolIsSynchronized(symbol))
   {
      reason = "simbolo nao sincronizado";
      return false;
   }

   ENUM_SYMBOL_TRADE_MODE tradeMode =
      (ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(
         symbol,
         SYMBOL_TRADE_MODE
      );

   if(tradeMode == SYMBOL_TRADE_MODE_DISABLED ||
      tradeMode == SYMBOL_TRADE_MODE_CLOSEONLY)
   {
      reason = "negociacao desactivada no simbolo";
      return false;
   }

   // lote
   if(lot <= 0.0)
   {
      reason = "lote invalido";
      return false;
   }

   double minLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_MIN
      );

   double maxLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_MAX
      );

   double stepLot =
      SymbolInfoDouble(
         symbol,
         SYMBOL_VOLUME_STEP
      );

   if(stepLot <= 0.0)
      stepLot = minLot;

   // A tolerância de 1e-8 é obrigatória: 0.01/0.01 não é exacto em binário
   // e MathFloor(lot/step)*step pode devolver 0.00999999999. Sem ela, este
   // portão recusaria TODAS as entradas - falso negativo medido em outros
   // pontos do EA, não hipótese.
   if(lot < minLot - 1e-8 || (maxLot > 0.0 && lot > maxLot + 1e-8))
   {
      reason = StringFormat(
         "lote %.3f fora da faixa %.3f..%.3f",
         lot, minLot, maxLot
      );
      return false;
   }

   if(stepLot > 0.0)
   {
      double passos = lot / stepLot;

      if(MathAbs(passos - MathRound(passos)) > 1e-8)
      {
         reason = StringFormat(
            "lote %.3f nao e multiplo do step %.3f",
            lot, stepLot
         );
         return false;
      }
   }

   // cotações reais
   double ask =
      SymbolInfoDouble(
         symbol,
         SYMBOL_ASK
      );

   double bid =
      SymbolInfoDouble(
         symbol,
         SYMBOL_BID
      );

   double point =
      SymbolInfoDouble(
         symbol,
         SYMBOL_POINT
      );

   if(ask <= 0.0 || bid <= 0.0 || point <= 0.0)
   {
      reason = "cotacao indisponivel";
      return false;
   }

   // stops mínimos do broker
   // slPoints == 0 é a entrada sem stop declarada (EnableStoplessEntry): a
   // armadura vem depois. Não é erro - o mínimo do broker só se exige quando
   // existe stop na ordem.
   if(slPoints > 0.0)
   {
      long stopLevel =
         SymbolInfoInteger(
            symbol,
            SYMBOL_TRADE_STOPS_LEVEL
         );

      if(slPoints < (double)stopLevel - 1e-8)
      {
         reason = StringFormat(
            "SL %.0f pts abaixo do StopLevel %d do broker",
            slPoints, (int)stopLevel
         );
         return false;
      }
   }

   return true;

}



// Assinatura original da v1.2.9. Mantida porque é pública dentro do projecto
// e há ficheiros que a podem voltar a chamar; o portão real é o de cima.
bool ValidateSymbol(
   const string symbol,
   double lot,
   double slPoints
)
{
   string reason = "";

   return ValidateSymbol(symbol, lot, slPoints, reason);
}



#endif
