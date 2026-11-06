// XAU_AI_PRO v1.2.49
#ifndef HEALTHMONITOR_MQH
#define HEALTHMONITOR_MQH

#include "../Core/Config.mqh"
#include "../Enterprise/Telemetry.mqh"   // ETAPA 15.6.5: ENUM_TELEMETRY_STATE compartilhado
#include "Logger.mqh"

//==================================================
// XAU_AI_PRO � HEALTH MONITOR (ETAPA 6)
// Sistema central de monitoramento de sa�de.
//
// Absorveu o antigo WatchDog.mqh: heartbeat dos
// modulos ATR / ADX / RSI / AI / PYTHON / CSV / JSON
// com timeout e contagem de falhas.
//==================================================

//==================================================
// CONTADORES DE ERRO
//==================================================

int g_healthBrokerErrors    = 0;
int g_healthAIErrors        = 0;
int g_healthDatasetErrors   = 0;
int g_healthFileErrors      = 0;
int g_healthJSONErrors      = 0;
int g_healthPythonErrors    = 0;
int g_healthIndicatorErrors = 0;

//==================================================
// TICK MONITOR
//==================================================

datetime g_lastTickTime      = 0;
datetime g_lastSecond        = 0;
datetime g_lastHealthCheck   = 0;

int g_ticksPerSecond         = 0;
int g_ticksThisSecond        = 0;

//==================================================
// UPTIME / M�TRICAS (ETAPA 6)
//==================================================

datetime g_healthUptimeStart = 0;
ulong    g_healthTotalTicks  = 0;
ulong    g_healthCheckCount  = 0;
bool     g_healthLastCheckOK = true;
int      g_healthConsecutiveFails = 0;   // F4/P1-1: falhas consecutivas p/ backoff exponencial

//==================================================
// WATCHDOG � HEARTBEAT DOS M�DULOS (ETAPA 6)
// Absorvido do antigo WatchDog.mqh
//==================================================

#define HEALTH_WD_MODULES      7
#define HEALTH_WD_MAX_FAILURES 3
#define HEALTH_BACKOFF_BASE_SEC  2      // F4/P1-1: fator base do backoff exponencial
#define HEALTH_BACKOFF_MAX_LEVEL 5      // F4/P1-1: nivel maximo de backoff (2^5 = 32x)

string g_wdModuleNames[HEALTH_WD_MODULES] = {"ATR", "ADX", "RSI", "AI", "PYTHON", "CSV", "JSON"};
ulong  g_wdLastTime[HEALTH_WD_MODULES];
int    g_wdFailures[HEALTH_WD_MODULES];
bool   g_wdActive[HEALTH_WD_MODULES];

// PIPELINE PROGRESS (LIVENESS vs PROGRESS): canal separado para modulos
// de dataset/python (CSV/JSON/PYTHON). g_wdLastTime registra liveness do EA;
// g_wdLastProgress registra avanzo real pos-UpdateDataset (progresso).
ulong  g_wdLastProgress[HEALTH_WD_MODULES];
int    g_wdProgressFails[HEALTH_WD_MODULES];

//==================================================
// ESTADO
//==================================================

bool g_healthInitialized = false;
bool g_healthStatus      = true;

//==================================================
// �NDICE DO M�DULO
//==================================================

int HealthModuleIndex(string module)
{
   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      if(StringCompare(g_wdModuleNames[i], module, false) == 0)
         return i;
   }

   return -1;
}

//==================================================
// INIT
//==================================================

bool HealthMonitorInit()
{
   datetime now = TimeCurrent();

   // v1.2.49 (P1.24): o watchdog carimba no relogio que avanca sempre.
   // TimeCurrent() e a hora do ULTIMO tick: sem cotacao fica parada e os
   // intervalos medidos com ela nunca vencem (ver HealthClockNow).
   datetime wdNow = HealthClockNow();

   g_lastTickTime      = wdNow;
   g_lastSecond        = now;
   g_lastHealthCheck   = wdNow;
   g_healthUptimeStart = now;

   g_ticksPerSecond  = 0;
   g_ticksThisSecond = 0;

   g_healthTotalTicks  = 0;
   g_healthCheckCount  = 0;
   g_healthLastCheckOK = true;
   g_healthConsecutiveFails = 0;

   // WatchDog (ETAPA 6)
   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      g_wdLastTime[i] = 0;
      g_wdFailures[i] = 0;
      g_wdActive[i]   = true;
      g_wdLastProgress[i]   = 0;
      g_wdProgressFails[i]  = 0;
   }

   g_healthStatus      = true;
   g_healthInitialized = true;

   LogSystem("HealthMonitor inicializado (WatchDog integrado)");

   return true;
}

//==================================================
// UPDATE TICKS
//==================================================

void HealthMonitorUpdateTicks()
{
   if(!g_healthInitialized)
      return;

   datetime now = TimeCurrent();

   // v1.2.49: a idade do ultimo tick passa a ser medida no relogio real - o do
   // servidor e exactamente aquilo que congela quando nao ha ticks.
   g_lastTickTime = HealthClockNow();
   g_healthTotalTicks++;

   MqlDateTime currentTime;
   MqlDateTime previousTime;

   TimeToStruct(now, currentTime);
   TimeToStruct(g_lastSecond, previousTime);

   // Novo segundo
   if(currentTime.sec != previousTime.sec)
   {
      g_ticksPerSecond  = g_ticksThisSecond;
      g_ticksThisSecond = 0;
      g_lastSecond      = now;
   }

   g_ticksThisSecond++;
}

//==================================================
// TICK TIMEOUT
//==================================================

bool HealthMonitorCheckTickTimeout(int maxSeconds = 10)
{
   if(!g_healthInitialized)
      return false;

   datetime now = HealthClockNow();

   int secondsSinceLastTick = (int)(now - g_lastTickTime);

   if(secondsSinceLastTick > maxSeconds)
   {
      LogError(
         "HealthMonitor: timeout de tick",
         "Seconds=" + IntegerToString(secondsSinceLastTick)
      );

      return false;
   }

   return true;
}

//==================================================
// REGISTRO DE ERRO
//==================================================

void HealthMonitorLogError(string module)
{
   if(module == "BROKER")
      g_healthBrokerErrors++;
   else if(module == "AI")
      g_healthAIErrors++;
   else if(module == "DATASET")
      g_healthDatasetErrors++;
   else if(module == "FILE")
      g_healthFileErrors++;
   else if(module == "JSON")
      g_healthJSONErrors++;
   else if(module == "PYTHON")
      g_healthPythonErrors++;
   else if(module == "INDICATOR")
      g_healthIndicatorErrors++;
   else
   {
      LogWarning(
         "HealthMonitor: modulo desconhecido",
         "Module=" + module
      );
   }
}

//==================================================
// HEARTBEAT (ETAPA 6 � absorve WatchDogHeartbeat)
//==================================================

void HealthMonitorHeartbeat(string module)
{
   if(!g_healthInitialized)
      return;

   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return;

   g_wdLastTime[idx] = GetTickCount64();
   g_wdFailures[idx] = 0;
}

//==================================================
// PIPELINE PROGRESS (F4/1.2 -- LIVENESS vs PROGRESS)
// A diferencia do Heartbeat (liveness do EA), este rexistro so avanza cando
// o pipeline de dataset/python realmente executou (pos-UpdateDataset).
// Permite detectar parada real do pipeline sen disparar o falso HEALTH_FAILURE
// cando o trading esta bloqueado por un early-return lexitimo (ex.: SAFETY 20/20).
//==================================================

void HealthMonitorProgress(string module)
{
   if(!g_healthInitialized)
      return;

   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return;

   g_wdLastProgress[idx] = GetTickCount64();
   g_wdProgressFails[idx] = 0;
}

//==================================================
// E pipeline? (modulos que so fan progress pos-UpdateDataset)
//==================================================

bool HealthIsPipeline(int idx)
{
   if(idx < 0 || idx >= HEALTH_WD_MODULES)
      return false;

   string m = g_wdModuleNames[idx];
   if(m == "PYTHON" || m == "CSV" || m == "JSON")
      return true;

   return false;
}

//==================================================
// PIPELINE PROGRESS TIMEOUT (F4/1.2) [LIVENESS vs PROGRESS]
// Separado do liveness: a cadencia normal do pipeline e a cadencia
// de velas do timeframe (M1 ~60s, M5 ~300s, H1 ~3600s). O timeout
// de progresso DEBE superar esa cadencia para nao xerar HEALTH_FAILURE
// falso en produccion. 0 (default) => auto: 2x cadencia, minimo
// HealthWatchdogInterval. O tester/hook pode forzar outro valor
// (ex.: 20s) via input HealthPipelineProgressTimeout.
//==================================================

int HealthGetPipelineProgressTimeoutSec()
{
   if(HealthPipelineProgressTimeout > 0)
      return HealthPipelineProgressTimeout;

   int cadenceSec = PeriodSeconds(PERIOD_CURRENT);

   if(cadenceSec <= 0)
      cadenceSec = 300;   // fallback conservador (M5)

   int autoSec = cadenceSec * 2;

   if(autoSec < HealthWatchdogInterval)
      autoSec = HealthWatchdogInterval;

   return autoSec;
}

// RESET HEARTBEAT (ETAPA 6 � absorve WatchDogResetFailures)
//==================================================

void HealthMonitorResetHeartbeat(string module)
{
   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return;

   g_wdLastTime[idx] = 0;
   g_wdFailures[idx] = 0;
}

//==================================================
// CHECK HEARTBEAT DE UM M�DULO (ETAPA 6)
//==================================================

bool HealthMonitorCheckHeartbeatModule(int idx)
{
   if(idx < 0 || idx >= HEALTH_WD_MODULES)
      return true;

   if(!g_wdActive[idx])
      return true;

   // LIVENESS vs PROGRESS (F4/1.2): para modulos de pipeline usamos o canal
   // de progresso (avanza s� con UpdateDataset real). Para indicadores e AI
   // usamos o heartbeat de liveness (avanza cada tick do OnTick).
   bool isPipeline = HealthIsPipeline(idx);

   if(!isPipeline)
   {
      // M�dulo nunca enviou heartbeat -> n�o � falha
      if(g_wdLastTime[idx] == 0)
         return true;

      ulong now       = GetTickCount64();
      ulong timeoutMs = (ulong)HealthWatchdogInterval * 1000;

      if(now - g_wdLastTime[idx] > timeoutMs)
      {
         g_wdFailures[idx]++;

         if(g_wdFailures[idx] >= HEALTH_WD_MAX_FAILURES)
         {
            LogWarning(
               "HealthMonitor: modulo sem heartbeat",
               g_wdModuleNames[idx],
               "Segundos=" + IntegerToString((int)((now - g_wdLastTime[idx]) / 1000))
            );

            return false;
         }

         return true;
      }

      g_wdFailures[idx] = 0;

      return true;
   }
   else
   {
      // Pipeline nunca avanzou progress -> non � falha (permite bloqueo
      // lex�timo do trading; s� falla se xa avanzou e despois parou).
      if(g_wdLastProgress[idx] == 0)
         return true;

      // 04/11/2026 - P2.20: mercado FECHADO nao e pipeline parado.
      // MEDIDO 04/11 18:07 local (23:07 servidor): USDBRL M5 sem vela nova
      // desde 22:50, dataset.csv parado as 18:00:01, e os tres modulos de
      // pipeline (PYTHON/CSV/JSON) declarados "parado | Segundos=741" com o
      // EA a receber ticks (Segundos sem tick: 0). UpdateDataset() devolve
      // false enquanto iTime(...,0) nao muda, logo no fecho diario o
      // progresso congela por desenho. Os modulos de liveness (ATR/ADX/RSI/
      // AI) ja tinham esta guarda desde a v1.2.80; o ramo de pipeline nao.
      if(!HealthSymbolSessionOpen())
        {
         g_wdProgressFails[idx] = 0;
         return true;
        }

      ulong now       = GetTickCount64();
      ulong timeoutMs = (ulong)HealthGetPipelineProgressTimeoutSec() * 1000;

      if(now - g_wdLastProgress[idx] > timeoutMs)
      {
         g_wdProgressFails[idx]++;

         if(g_wdProgressFails[idx] >= HEALTH_WD_MAX_FAILURES)
         {
            LogWarning(
               "HealthMonitor: modulo de pipeline parado",
               g_wdModuleNames[idx],
               "Segundos=" + IntegerToString((int)((now - g_wdLastProgress[idx]) / 1000))
            );

            return false;
         }

         return true;
      }

      g_wdProgressFails[idx] = 0;

      return true;
   }
}

//==================================================
// CHECK HEARTBEATS (ETAPA 6 � absorve WatchDogRunCheck)
//==================================================

bool HealthMonitorCheckHeartbeats()
{
   bool allOK = true;

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      if(!HealthMonitorCheckHeartbeatModule(i))
         allOK = false;
   }

   return allOK;
}

//==================================================
// BACKOFF (F4/P1-1)
// Retorna o intervalo efetivo (segundos) entre checks com
// backoff exponencial baseado em falhas consecutivas:
//   nivel 0 -> HealthCheckInterval (nominal)
//   nivel n -> HealthCheckInterval * 2^n (limitado a MAX_LEVEL)
// Isso evita "storm" de checks repetidos durante uma falha
// sustentada, espacando as tentativas de recuperacao.
//==================================================

int HealthGetBackoffInterval(int baseIntervalSec)
{
   int level = g_healthConsecutiveFails;

   if(level < 0)
      level = 0;

   if(level > HEALTH_BACKOFF_MAX_LEVEL)
      level = HEALTH_BACKOFF_MAX_LEVEL;

   int multiplier = 1;

   for(int i = 0; i < level; i++)
      multiplier *= 2;

   return baseIntervalSec * multiplier;
}

//==================================================
// HEALTH CHECK
//==================================================

// v1.2.31 (30/10/2026) - P1.3/P0.4 rodada 3: este EA roda em 16 graficos
// multi-ativo. A maioria dos simbolos fica legitimamente sem tick (mercado
// fechado ou pouca liquidez) e HealthMonitorCheckTickTimeout(15) marcava
// FAILURE por isso. MEDIDO na v1.2.30 as 17:15: USDCOP com "Segundos sem
// tick: 661", "Total ticks: 0" e "Status: FAILURE" permanente, imprimindo o
// bloco completo a cada 300 s. Um alerta que nunca desliga nao alerta nada:
// vira o maior emissor do journal, esconde a falha real e ainda pode disparar
// Recovery/Notification sem causa.
// Agora o timeout de tick so reprova a saude quando HA sessao de cotacao
// aberta para o simbolo neste instante. Sessao desconhecida = comportamento
// antigo (reprova), para nao silenciar falha real de simbolo sem metadados.
//==================================================
// RELOGIO DO WATCHDOG (v1.2.49 - P1.24)
//==================================================
//
// MEDIDO em 31/10/2026 (sabado, mercado fechado desde sexta 23:59):
//   get_time_information -> trade_server_last_known_time = 2026-10-30T23:59:59
//   Logs\20261031.log    -> 726 linhas, ZERO blocos de HEALTH
//
// TimeCurrent() nao e "agora": e a hora do ULTIMO tick recebido. Com o mercado
// fechado fica parada, logo (now - g_lastHealthCheck) = 0 para sempre e o health
// check - o unico watchdog que pode notar um terminal morto ou desligado -
// simplesmente nao volta a correr. Num EA que tem de viver 24/7 isso significa
// que uma falha que comeca na sexta so pode ser notada na segunda, com 60 horas
// de atraso.
//
// TimeLocal() e o relogio do computador: nao depende de cotacao e avanca sempre.
// E o correcto para medir DURACOES (intervalo entre checks, idade do ultimo tick).
// A hora do servidor continua a ser a de referencia para tudo o que e de mercado
// (sessoes, horas de evasao, reset diario) - essas continuam em TimeCurrent().
datetime HealthClockNow()
{
   return (datetime)TimeLocal();
}

// Hora de referencia para decidir se HA sessao de mercado aberta. Tem de
// avancar quando o servidor nao manda ticks, senao o dia da semana nunca muda
// ao fim de semana. TimeTradeServer() e uma estimativa feita no cliente com
// base no relogio local e na ultima hora conhecida do servidor; devolve 0
// quando nao a consegue calcular, e nesse caso fica o criterio antigo.
datetime HealthSessionNow()
{
   datetime srv = TimeTradeServer();

   if(srv > 0)
      return srv;

   return TimeCurrent();
}

bool HealthSymbolSessionOpen()
{
   MqlDateTime dt;

   // v1.2.49 (P1.24): TimeCurrent() e a hora do ultimo tick; ao fim de semana
   // fica em sexta 23:59:59, o que fazia a sessao de sexta parecer ABERTA e
   // reprovava a saude por "sem tick" precisamente nos dias sem cotacao.
   // TimeTradeServer() e a hora do servidor estimada no cliente e avanca mesmo
   // sem ticks. Se nao estiver disponivel (0), mantem-se o criterio antigo.
   TimeToStruct(HealthSessionNow(), dt);

   long agora = (long)dt.hour * 3600 + (long)dt.min * 60 + (long)dt.sec;

   for(int i = 0; i < 8; i++)
     {
      datetime ini = 0, fim = 0;

      if(!SymbolInfoSessionQuote(_Symbol, (ENUM_DAY_OF_WEEK)dt.day_of_week, i, ini, fim))
        {
         // Sem metadados de sessao: nao presume folga, mantem o criterio antigo.
         if(i == 0)
            return true;
         break;
        }

      long abre  = (long)ini % 86400;
      long fecha = (long)fim % 86400;

      if(fecha < abre)          // sessao que cruza a meia-noite
        {
         if(agora >= abre || agora <= fecha)
            return true;
        }
      else
        {
         if(agora >= abre && agora <= fecha)
            return true;
        }
     }

   return false;
}

bool HealthMonitorCheck()
{
   if(!g_healthInitialized)
      return false;

   // v1.2.49 (P1.24): relogio do watchdog, nao a hora do ultimo tick.
   datetime now = HealthClockNow();

   // N�o executa an�lise completa em todos os ticks.
   // F4/P1-1: intervalo efetivo cresce com backoff quando ha
   // falhas consecutivas, espacando retentativas.
   int effectiveInterval = HealthGetBackoffInterval(HealthCheckInterval);

   if(now - g_lastHealthCheck < effectiveInterval)
      return g_healthStatus;

   g_lastHealthCheck = now;
   g_healthCheckCount++;

   bool healthy = true;

   //================================================
   // TICK
   //================================================

   // v1.2.31: sem sessao aberta, "sem tick" e o estado normal do simbolo.
   //
   // v1.2.80 (P1.67): o resultado fica guardado para ser usado UMA vez so. O
   // MESMO "sem tick" era avaliado duas vezes com regras opostas - aqui
   // perdoado quando a sessao esta fechada, e na chamada a
   // HealthMonitorCheckHeartbeats() sem guarda nenhuma. MEDIDO em 02/11/2026
   // no USDBRL/M5: "Total ticks: 0 | Segundos sem tick: 14641" com
   // "Status: HEALTHY" numa passagem e "Status: FAILURE | Backoff: nivel=11
   // intervalo_efetivo=1920s" noutra, para o mesmo dado.
   bool tickEmFalta = !HealthMonitorCheckTickTimeout(15);
   if(tickEmFalta)
   {
      if(HealthSymbolSessionOpen())
      {
         LogWarning("HealthMonitor: tick timeout");
         healthy = false;
      }
   }

   //================================================
   // HEARTBEATS (WatchDog integrado � ETAPA 6)
   //================================================

   // v1.2.80 (P1.67): sem tick NENHUM modulo avanca - ATR, ADX, RSI e AI so
   // progridem dentro de OnTick, e sem tick nao ha OnTick. Contar isso como
   // falha independente repetia o mesmo dado que o teste de tick ja avaliou e,
   // pior, escalava o backoff: medido no USDBRL/M5 "Backoff: nivel=11
   // intervalo_efetivo=1920s", ou seja o watchdog passava a olhar aquele
   // grafico de 32 em 32 minutos. Sem tick a falha dos modulos e CONSEQUENCIA;
   // com tick continua a valer como antes, e o contador de falhas interno de
   // HealthMonitorCheckHeartbeats() segue intacto.
   if(!HealthMonitorCheckHeartbeats())
   {
      if(!tickEmFalta)
         healthy = false;
   }

   //================================================
   // BROKER
   //================================================

   if(g_healthBrokerErrors > 5)
   {
      LogError("HealthMonitor: erros de broker", IntegerToString(g_healthBrokerErrors));
      healthy = false;
   }

   //================================================
   // AI
   //================================================

   if(g_healthAIErrors > 3)
   {
      LogError("HealthMonitor: erros de IA", IntegerToString(g_healthAIErrors));
      healthy = false;
   }

   //================================================
   // DATASET
   //================================================

   if(g_healthDatasetErrors > 2)
   {
      LogError("HealthMonitor: erros de dataset", IntegerToString(g_healthDatasetErrors));
      healthy = false;
   }

   //================================================
   // FILE
   //================================================

   if(g_healthFileErrors > 2)
   {
      LogError("HealthMonitor: erros de arquivo", IntegerToString(g_healthFileErrors));
      healthy = false;
   }

   //================================================
   // JSON
   //================================================

   if(g_healthJSONErrors > 2)
   {
      LogError("HealthMonitor: erros de JSON", IntegerToString(g_healthJSONErrors));
      healthy = false;
   }

   //================================================
   // PYTHON
   //================================================

   if(g_healthPythonErrors > 1)
   {
      LogError("HealthMonitor: erros de Python", IntegerToString(g_healthPythonErrors));
      healthy = false;
   }

   //================================================
   // INDICADORES
   //================================================

   if(g_healthIndicatorErrors > 5)
   {
      LogError("HealthMonitor: erros de indicadores", IntegerToString(g_healthIndicatorErrors));
      healthy = false;
   }

   //================================================
   // RESULTADO
   //================================================

   g_healthStatus      = healthy;
   g_healthLastCheckOK = healthy;

   // F4/P1-1: atualiza o contador de falhas consecutivas p/ backoff
   if(!healthy)
      g_healthConsecutiveFails++;
   else
      g_healthConsecutiveFails = 0;

   // ETAPA 15.6.5: ponte com telemetria real �
   // falha de health alimenta o contador global de erros.
   if(!healthy)
      CTelemetry::RecordError();

   if(healthy)
      LogInfo("HealthMonitor: HEALTH OK");
   else
      LogWarning("HealthMonitor: HEALTH FAILURE");

   return healthy;
}

//==================================================
// GETTERS
//==================================================

int HealthGetBrokerErrors()
{
   return g_healthBrokerErrors;
}

int HealthGetAIErrors()
{
   return g_healthAIErrors;
}

int HealthGetDatasetErrors()
{
   return g_healthDatasetErrors;
}

int HealthGetFileErrors()
{
   return g_healthFileErrors;
}

int HealthGetJSONErrors()
{
   return g_healthJSONErrors;
}

int HealthGetPythonErrors()
{
   return g_healthPythonErrors;
}

int HealthGetIndicatorErrors()
{
   return g_healthIndicatorErrors;
}

//==================================================
// TICK METRICS
//==================================================

int HealthGetTicksPerSecond()
{
   return g_ticksPerSecond;
}

int HealthGetSecondsSinceTick()
{
   if(!g_healthInitialized)
      return -1;

   return (int)(HealthClockNow() - g_lastTickTime);
}

//==================================================
// UPTIME / M�TRICAS (ETAPA 6)
//==================================================

ulong HealthGetTotalTicks()
{
   return g_healthTotalTicks;
}

datetime HealthGetUptimeStart()
{
   return g_healthUptimeStart;
}

int HealthGetUptimeSeconds()
{
   if(!g_healthInitialized)
      return 0;

   return (int)(TimeCurrent() - g_healthUptimeStart);
}

ulong HealthGetCheckCount()
{
   return g_healthCheckCount;
}

bool HealthGetLastCheckOK()
{
   return g_healthLastCheckOK;
}

//==================================================
// HEARTBEAT FAILURES (ETAPA 6)
//==================================================

int HealthGetHeartbeatFailures(string module)
{
   int idx = HealthModuleIndex(module);

   if(idx < 0)
      return 0;

   return g_wdFailures[idx];
}

//==================================================
// STATUS
//==================================================

bool HealthIsHealthy()
{
   return g_healthStatus;
}

//==================================================
// ESTADO MULTI-NIVEL (ETAPA 15.6.5)
// Deriva HEALTHY/WARNING/ERROR a partir dos
// contadores e watchdogs. UNAVAILABLE quando o
// monitor nao foi inicializado.
//==================================================

ENUM_TELEMETRY_STATE HealthGetState()
{
   if(!g_healthInitialized)
      return TM_UNAVAILABLE;

   // Falha estrutural do ultimo check
   if(!g_healthStatus)
      return TM_ERROR;

   // WARNING: erros presentes, abaixo dos limites criticos
   int totalErr = g_healthBrokerErrors + g_healthAIErrors +
                  g_healthDatasetErrors + g_healthFileErrors +
                  g_healthJSONErrors  + g_healthPythonErrors +
                  g_healthIndicatorErrors;

   if(totalErr > 0)
      return TM_WARNING;

   // v1.2.82 (02/11/2026) - P1.69: o P1.67 curou a atribuicao de `healthy`,
   // mas os contadores dos watchdogs continuavam a subir SEM tick (ATR, ADX,
   // RSI e IA so avancam dentro de OnTick), logo HealthGetStateString()
   // respondia WARNING para o MESMO dado que o resumo chamava HEALTHY - o
   // defeito "um dado, dois veredictos" vivido uma camada acima. MEDIDO no
   // journal de 02/11 as 15:54: "[HEALTH] WARNING | ... | Status: HEALTHY |
   // ... | ATR: 1 falhas" nos quatro graficos sem tick (USDBRL/M5, USDCOP/H1,
   // USDCLP/H1, USDRUB/H1). Sem tick nao ha evidencia de falha de modulo:
   // enquanto HealthGetSecondsSinceTick() > 15 as falhas dos watchdogs nao
   // contam para o veredicto. O contador continua a ser somado e continua a
   // sair impresso - muda apenas o veredicto.
   bool houveTick = (HealthGetSecondsSinceTick() <= 15);
   for(int i = 0; i < HEALTH_WD_MODULES && houveTick; i++)
   {
      if(g_wdFailures[i] > 0 && g_wdFailures[i] < HEALTH_WD_MAX_FAILURES)
         return TM_WARNING;
   }

   return TM_HEALTHY;
}

string HealthGetStateString()
{
   switch(HealthGetState())
   {
      case TM_HEALTHY:     return "HEALTHY";
      case TM_WARNING:     return "WARNING";
      case TM_ERROR:       return "ERROR";
      case TM_SAFE:        return "SAFE";
      case TM_RECOVERY:    return "RECOVERY";
      case TM_UNAVAILABLE: return "UNAVAILABLE";
   }
   return "UNAVAILABLE";
}

//==================================================
// SUMMARY
//==================================================

string HealthMonitorSummary()
{
   string summary = "=== HEALTH MONITOR ===\n";

   // v1.2.82 (02/11/2026) - P1.69: a linha Status lia g_healthStatus e o tag
   // lia HealthGetStateString(), por isso a MESMA linha podia dizer
   // "[HEALTH] WARNING | ... | Status: HEALTHY". Passa a ler a mesma fonte.
   summary += "Status: " + HealthGetStateString() +
              " (check " + (g_healthStatus ? "OK" : "FALHOU") + ")\n";
   summary += "Uptime (s): " + IntegerToString(HealthGetUptimeSeconds()) + "\n";
   summary += "Ticks/seg: " + IntegerToString(g_ticksPerSecond) + "\n";
   summary += "Total ticks: " + IntegerToString((long)g_healthTotalTicks) + "\n";
   summary += "Checks: " + IntegerToString((long)g_healthCheckCount) + "\n";
   summary += "Segundos sem tick: " + IntegerToString(HealthGetSecondsSinceTick()) + "\n";
   summary += "Backoff: nivel=" + IntegerToString(g_healthConsecutiveFails) +
              " intervalo_efetivo=" + IntegerToString(HealthGetBackoffInterval(HealthCheckInterval)) + "s\n\n";

   summary += "--- Heartbeats ---\n";

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      // 04/11/2026 - P2.20: o resumo imprimia g_wdFailures (liveness) tambem
      // para os modulos de pipeline, que acumulam em g_wdProgressFails. A
      // mesma mensagem dizia "Status: ERROR (check FALHOU)" e
      // "PYTHON: 0 falhas | CSV: 0 falhas | JSON: 0 falhas". Passa a ler o
      // contador que o veredicto realmente usa.
      int falhasModulo = HealthIsPipeline(i) ? g_wdProgressFails[i]
                                             : g_wdFailures[i];
      summary += g_wdModuleNames[i] + ": " + IntegerToString(falhasModulo) + " falhas\n";
   }

   summary += "\n--- Erros ---\n";

   summary += "Broker errors: " + IntegerToString(g_healthBrokerErrors) + "\n";
   summary += "AI errors: " + IntegerToString(g_healthAIErrors) + "\n";
   summary += "Dataset errors: " + IntegerToString(g_healthDatasetErrors) + "\n";
   summary += "File errors: " + IntegerToString(g_healthFileErrors) + "\n";
   summary += "JSON errors: " + IntegerToString(g_healthJSONErrors) + "\n";
   summary += "Python errors: " + IntegerToString(g_healthPythonErrors) + "\n";
   summary += "Indicator errors: " + IntegerToString(g_healthIndicatorErrors);

   return summary;
}

//==================================================
// RESET ERRORS
//==================================================

void HealthMonitorResetErrors()
{
   g_healthBrokerErrors    = 0;
   g_healthAIErrors        = 0;
   g_healthDatasetErrors   = 0;
   g_healthFileErrors      = 0;
   g_healthJSONErrors      = 0;
   g_healthPythonErrors    = 0;
   g_healthIndicatorErrors = 0;

   for(int i = 0; i < HEALTH_WD_MODULES; i++)
   {
      g_wdFailures[i] = 0;
   }

   g_healthStatus      = true;
   g_healthLastCheckOK = true;
   g_healthConsecutiveFails = 0;

   LogSystem("HealthMonitor: contadores resetados");
}

//==================================================
// SHUTDOWN
//==================================================

void HealthMonitorShutdown()
{
   LogSystem(
      "HealthMonitor finalizado | Uptime(s)=" +
      IntegerToString(HealthGetUptimeSeconds()) +
      " | Ticks=" +
      IntegerToString((long)g_healthTotalTicks)
   );

   g_healthInitialized = false;
}

#endif
