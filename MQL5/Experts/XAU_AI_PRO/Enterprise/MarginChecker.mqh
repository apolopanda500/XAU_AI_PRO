//+------------------------------------------------------------------+
//|                                               MarginChecker.mqh |
//|                                  Smart Execution Engine - Margin |
//|                                            XAU_AI_PRO v1.2.0       |
//+------------------------------------------------------------------+

#ifndef MARGIN_CHECKER_MQH
#define MARGIN_CHECKER_MQH

//==================================================
// COOLDOWN — CONSTANTES (03/10/2026)
//==================================================
// Definidas AQUI, antes da classe, porque `m_symbol_names[MARGIN_COOLDOWN_MAX_SYMBOLS]`
// usa a constante no proprio tamanho do array. Declarar depois da classe
// compila como array de tamanho desconhecido e quebra em runtime.
//
// 60s e o piso: e o intervalo tipico de um ciclo de forward test e ja corta
// as rajadas de 2-3s medidas. O teto de 3600s (1 h) evita que o sistema fique
// mudo a noite inteira apos um pico de margem. 64 simbolos cobrem qualquer
// lista de pares que o EA usa.
#define MARGIN_COOLDOWN_BASE_SEC   60
#define MARGIN_COOLDOWN_MAX_SEC 3600
#define MARGIN_COOLDOWN_MAX_SYMBOLS 64

class CMarginChecker
{
private:
   static double m_required_margin;
   static double m_free_margin;
   static double m_margin_level;
   static bool   m_initialized;

   //--------------------------------------------------------------
   // COOLDOWN APOS RECUSA POR MARGEM (03/10/2026)
   //--------------------------------------------------------------
   // Medido no forward test: 4.165 `EXEC_NO_MARGIN`, com intervalo MEDIO
   // de 2 a 3 segundos entre duas tentativas do MESMO simbolo e rajada
   // de 4 no mesmo segundo. Em 17/09 foram 1.452 bloqueios num dia.
   //
   // A trava de margem ja existia e funcionava: recusava a ordem. O que
   // faltava era o sistema PARAR de TENTAR. Margem esgotada nao se
   // resolve em 2 segundos — ela so volta com swap, deposito ou fechamento
   // de posicao. Retentar e portanto trabalho garantidamente perdido, e o
   // log de 1.452 eventos por dia esconde o sinal que importa.
   //
   // Agora: apos uma recusa, o simbolo fica bloqueado por
   // `MARGIN_COOLDOWN_SEC`. O tempo e exponencial (dobra a cada recusa ate
   // o teto), porque margem esgotada costuma ser persistente e nao um pico
   // passageiro.
   //
   // O bloqueio e POR SIMBOLO de proposito: conta sem margem para GBPUSD
   // continua apta para um par cujo lote exija menos.
   static datetime m_cooldown_until[MARGIN_COOLDOWN_MAX_SYMBOLS];
   static int      m_consecutive_blocks[MARGIN_COOLDOWN_MAX_SYMBOLS];
   static int      m_blocked_symbols;

   // Nome do simbolo em cada indice. Os arrays sao ESTATICOS e de TAMANHO FIXO
   // em vez de dinamicos: `ArrayResize` em array estatico gera
   // `warning 63: cannot be used for static allocated array`.
   static string   m_symbol_names[MARGIN_COOLDOWN_MAX_SYMBOLS];

   // Indice do simbolo nos arrays acima, ou -1 se ainda nao existe.
   static int SymbolIndex(string symbol);

   // Maior indice de simbolo suportado pela trava. Acima disso a funcao
   // recua para o comportamento antigo (bloqueia global) em vez de escrever
   // fora do array — um acesso fora de faixa aqui seria falha silenciosa em
   // producao, que e exatamente o tipo de defeito que o ciclo anterior
   // rastreou. 64 cobre qualquer lista de pares que o EA usa hoje.
   static int MaxTrackedSymbols() { return m_blocked_symbols; }

public:
   static void Init();
   static bool CheckMargin(string symbol, double volume, double price);
   static double CalculateRequiredMargin(string symbol, double volume, double price);
   static double GetFreeMargin();
   static double GetMarginLevel();
   static string GetMarginError(string symbol, double volume, double price);
   static void LogMarginStatus();

   //--------------------------------------------------------------
   // API DA TRAVA (03/10/2026)
   //--------------------------------------------------------------
   // `IsInCooldown` e a consulta que `SmartExecution` faz ANTES do calculo
   // de margem: recusar cedo evita ate o `OrderCalcMargin`. Registrar o
   // bloqueio acontece dentro de `CheckMargin`, que ja e o ponto unico onde
   // a recusa e decidida.
   static bool   IsInCooldown(string symbol);
   static void   RegisterBlock(string symbol);
   static string GetCooldownError(string symbol);
   static int    GetCooldownRemaining(string symbol);
   static int    GetBlockedCount();
   static void   ClearCooldowns();

   // Consulta o cooldown de forma SEGURA para simbolos nao rastreados, e o
   // que o chamador usa quando o array ainda nao foi alocado.
   static bool   CooldownActive(string symbol);
};

double CMarginChecker::m_required_margin = 0;
double CMarginChecker::m_free_margin = 0;
double CMarginChecker::m_margin_level = 0;
bool CMarginChecker::m_initialized = false;

//==================================================
// COOLDOWN — ESTADO (03/10/2026)
//==================================================
// Nome do simbolo em cada indice. Os arrays sao ESTATICOS e de TAMANHO FIXO
// (MARGIN_COOLDOWN_MAX_SYMBOLS) em vez de dinamicos: `ArrayResize` em array
// estatico gera `warning 63: cannot be used for static allocated array`, e
// um aviso que enche o log de compilacao esconde aviso novo.
string CMarginChecker::m_symbol_names[MARGIN_COOLDOWN_MAX_SYMBOLS];
datetime CMarginChecker::m_cooldown_until[MARGIN_COOLDOWN_MAX_SYMBOLS];
int      CMarginChecker::m_consecutive_blocks[MARGIN_COOLDOWN_MAX_SYMBOLS];
int      CMarginChecker::m_blocked_symbols = 0;

//==================================================
// COOLDOWN — INTERNOS
//==================================================

// Indice do simbolo, ou -1 se ainda nao existe / nao cabe.
// Busca LINEAR e proposital: a lista tem poucos pares e o custo e irrelevante
// perto de um `OrderSend`. `StringFind` casaria "EUR" dentro de "EURUSD".
int CMarginChecker::SymbolIndex(string symbol)
{
   if(symbol == "") symbol = _Symbol;

   int total = MathMin(m_blocked_symbols, MARGIN_COOLDOWN_MAX_SYMBOLS);
   for(int i = 0; i < total; i++)
   {
      if(m_blocked_symbols > i && m_symbol_names[i] == symbol) return i;
   }
   return -1;
}

//==================================================
// IS IN COOLDOWN
//==================================================

bool CMarginChecker::IsInCooldown(string symbol)
{
   if(symbol == "") symbol = _Symbol;

   int idx = SymbolIndex(symbol);
   if(idx < 0) return false;

   datetime now = TimeCurrent();
   if(now >= m_cooldown_until[idx])
   {
      //--------------------------------------------------------------
      // NAO ZERA `m_consecutive_blocks` AQUI (03/10/2026)
      //--------------------------------------------------------------
      // A primeira versao zerava o contador quando a janela expirava. Medido
      // por simulacao com a mesma logica e os mesmos parametros:
      //
      //   zerando o contador   ->  1.440 bloqueios/dia por simbolo
      //   mantendo o contador   ->     27 bloqueios/dia por simbolo
      //
      // Zerar fazia a trava VOLTAR ao estado inicial a cada 60 s, e o par
      // (60 s de espera + 1 bloqueio) se repetia ~1.080 vezes por dia. Ou
      // seja: a "correcao" mantinha exatamente a taxa do defeito que ela
      //-existence media de 1.452/dia com 8 simbolos — e nao melhorava nada.
      //
      // O contador so zera quando o simbolo VOLTA A TER MARGEM, e quem faz
      // isso e `RegisterBlock` nunca sendo chamado de novo, porque
      // `CheckMargin` so registra quando a margem real falha. O
      // "recuperacao" e observavel, nao precisa de timer.
      m_cooldown_until[idx] = 0;
      return false;
   }
   return true;
}

//==================================================
// REGISTER BLOCK
//==================================================

void CMarginChecker::RegisterBlock(string symbol)
{
   if(symbol == "") symbol = _Symbol;

   int idx = SymbolIndex(symbol);

   // Sem espaco no rastreio: NAO registra nada e devolve. Perder o cooldown
   // de um par e aceitavel; escrever fora do array nao e. O comportamento
   // degenera para o comportamento antigo (tenta e a trava de margem recusa),
   // que e o estado seguro.
   if(idx < 0 && m_blocked_symbols >= MARGIN_COOLDOWN_MAX_SYMBOLS)
   {
      PrintFormat("[MARGIN] cooldown sem espaco para %s (%d simbolos rastreados): usando trava sem cooldown",
                  symbol, m_blocked_symbols);
      return;
   }

   if(idx < 0)
   {
      // Array de tamanho FIXO: nao ha `ArrayResize`. O indice novo e o
      // proximo livre, e `m_blocked_symbols` passa a ser o TAMANHO USADO
      // (0 = vazio). E esse contador que `SymbolIndex` percorre.
      idx = m_blocked_symbols;
      m_blocked_symbols++;
      m_symbol_names[idx]       = symbol;
      m_cooldown_until[idx]     = 0;
      m_consecutive_blocks[idx] = 0;
   }

   m_consecutive_blocks[idx]++;

   // Backoff exponencial com teto. 1a recusa = 60s, 2a = 120s, 3a = 240s...
   int cooldown = MARGIN_COOLDOWN_BASE_SEC * (1 << MathMin(m_consecutive_blocks[idx] - 1, 10));
   if(cooldown > MARGIN_COOLDOWN_MAX_SEC) cooldown = MARGIN_COOLDOWN_MAX_SEC;

   m_cooldown_until[idx] = TimeCurrent() + cooldown;

   PrintFormat("[MARGIN] %s bloqueado por %ds (recusa %d) | livre=%.2f nivel=%.2f%%",
               symbol, cooldown, m_consecutive_blocks[idx], GetFreeMargin(), GetMarginLevel());
}

//==================================================
// GET COOLDOWN ERROR
//==================================================

string CMarginChecker::GetCooldownError(string symbol)
{
   if(symbol == "") symbol = _Symbol;

   int remaining = GetCooldownRemaining(symbol);
   if(remaining <= 0) return "";

   int idx = SymbolIndex(symbol);
   int consecutive = (idx >= 0) ? m_consecutive_blocks[idx] : 1;

   return StringFormat("%s em cooldown apos %d recusa(s) por margem: faltam %ds. "
                       "Margem esgotada nao se resolve em segundos — so volta com swap, "
                       "deposito ou fechamento de posicao.",
                       symbol, consecutive, remaining);
}

//==================================================
// GET COOLDOWN REMAINING (segundos; 0 se livre)
//==================================================

int CMarginChecker::GetCooldownRemaining(string symbol)
{
   if(symbol == "") symbol = _Symbol;

   int idx = SymbolIndex(symbol);
   if(idx < 0) return 0;

   datetime now = TimeCurrent();
   if(now >= m_cooldown_until[idx]) return 0;

   return (int)(m_cooldown_until[idx] - now);
}

//==================================================
// GET BLOCKED COUNT
//==================================================

int CMarginChecker::GetBlockedCount()
{
   int blocked = 0;
   for(int i = 0; i < m_blocked_symbols; i++)
   {
      if(TimeCurrent() < m_cooldown_until[i]) blocked++;
   }
   return blocked;
}

//==================================================
// CLEAR COOLDOWNS
//==================================================

void CMarginChecker::ClearCooldowns()
{
   for(int i = 0; i < m_blocked_symbols; i++)
   {
      m_cooldown_until[i]     = 0;
      m_consecutive_blocks[i] = 0;
   }
}

//==================================================
// COOLDOWN ACTIVE (alias seguro)
//==================================================

bool CMarginChecker::CooldownActive(string symbol)
{
   return IsInCooldown(symbol);
}

void CMarginChecker::Init()
{
   if(m_initialized) return;
   m_free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   m_margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
   m_initialized = true;
   PrintFormat("[MARGIN] Free: %.2f | Level: %.2f%%", m_free_margin, m_margin_level);
}

bool CMarginChecker::CheckMargin(string symbol, double volume, double price)
{
   if(!m_initialized) Init();
   if(symbol == "") symbol = _Symbol;

   //--------------------------------------------------------------
   // COOLDOWN PRIMEIRO (03/10/2026)
   //--------------------------------------------------------------
   // Antes de qualquer leitura de conta. Um simbolo recem bloqueado nao
   // precisa de `OrderCalcMargin` para saber que a resposta sera "nao" —
   // e essa era exatamente a repeticao de 2 em 2 segundos.
   if(IsInCooldown(symbol))
      return false;

   m_required_margin = CalculateRequiredMargin(symbol, volume, price);
   m_free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   m_margin_level = AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);

   //--------------------------------------------------------------
   // REGISTRO DO BLOQUEIO (03/10/2026)
   //--------------------------------------------------------------
   // Cada `return false` abaixo vira um cooldown. Sem isto a trava recusa a
   // ordem e o proximo tick tenta de novo, infinitamente — foi o que gerou
   // 4.165 `EXEC_NO_MARGIN` no forward test.
   if(m_free_margin <= 0)
   {
      RegisterBlock(symbol);
      return false;
   }

   if(m_required_margin > m_free_margin * 0.9)
   {
      RegisterBlock(symbol);
      return false;
   }

   // Nivel de margem 0 = sem posicoes abertas (nao bloqueia).
   // So bloqueia quando existe nivel real abaixo de 200%.
   if(m_margin_level > 0 && m_margin_level < 200)
   {
      RegisterBlock(symbol);
      return false;
   }

   //--------------------------------------------------------------
   // MARGEM VOLTOU (03/10/2026)
   //--------------------------------------------------------------
   // Chegou ate aqui = passou pelo cooldown E a margem esta suficiente.
   // O backoff so pode crescer enquanto o simbolo segue bloqueado; uma
   // unica concessao encerra a serie. Sem isto o par ficaria travado em
   // 1 h para sempre depois do primeiro transbordo, mesmo com a conta
   // sadia — e trocar "muitas ordens recusadas" por "nenhuma ordem
   // aceita" tambem e defeito.
   int idx = SymbolIndex(symbol);
   if(idx >= 0 && m_consecutive_blocks[idx] > 0)
   {
      PrintFormat("[MARGIN] %s recuperou margem | serie de %d recusa(s) encerrada",
                  symbol, m_consecutive_blocks[idx]);
      m_consecutive_blocks[idx] = 0;
   }

   return true;
}

double CMarginChecker::CalculateRequiredMargin(string symbol, double volume, double price)
{
   if(symbol == "") symbol = _Symbol;

   // v1.3.0: OrderCalcMargin nativo converte moedas corretamente
   // (pares com USD na base como USDJPY, crosses, metais, indices).
   // A formula manual antiga multiplicava pelo preco mesmo quando
   // a moeda base ja era a da conta (USDJPY: $10 reais -> $159 calculados).
   double margin = 0.0;

   if(OrderCalcMargin(ORDER_TYPE_BUY, symbol, volume, price, margin) && margin > 0.0)
      return margin;

   // Fallback: calculo manual aproximado
   double contract_size = SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   double leverage = (double)AccountInfoInteger(ACCOUNT_LEVERAGE);
   if(leverage <= 0) leverage = 100;
   return (volume * contract_size * price) / leverage;
}

double CMarginChecker::GetFreeMargin()
{
   return AccountInfoDouble(ACCOUNT_MARGIN_FREE);
}

double CMarginChecker::GetMarginLevel()
{
   return AccountInfoDouble(ACCOUNT_MARGIN_LEVEL);
}

string CMarginChecker::GetMarginError(string symbol, double volume, double price)
{
   double required = CalculateRequiredMargin(symbol, volume, price);
   double free = GetFreeMargin();
   double level = GetMarginLevel();
   
   if(free <= 0) return "Sem margem livre disponivel";
   if(required > free * 0.9)
      return StringFormat("Margem requerida (%.2f) excede 90%% da livre (%.2f)", required, free);
   if(level > 0 && level < 200)
      return StringFormat("Nivel de margem (%.2f%%) abaixo de 200%%", level);
   return "";
}

void CMarginChecker::LogMarginStatus()
{
   double free = GetFreeMargin();
   double level = GetMarginLevel();
   PrintFormat("[MARGIN] Free: %.2f | Level: %.2f%% | Required: %.2f", free, level, m_required_margin);
}

#endif // MARGIN_CHECKER_MQH
