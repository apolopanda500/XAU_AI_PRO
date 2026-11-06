#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""new_mq5_project.py -- gera a mao-de-obra minima de um projecto MQL5 modular.

Uso:
  python.exe new_mq5_project.py --name MEU_EA
  python.exe new_mq5_project.py --name MEU_EA --root "C:\...\MQL5\Files\Temp\Demo" --force
  python.exe new_mq5_project.py --list
  python.exe new_mq5_project.py --selftest

Gera (por omissao em MQL5\Experts\<NAME>\):
  <NAME>.mq5                  entrada OnInit/OnTick/OnDeinit (execucao DESLIGADA)
  Core\Config.mqh             constantes + normalizacao de volume
  Core\RiskCenter.mqh         risco por trade, perda diaria, drawdown
  Filters\SessionFilter.mqh   janela horaria
  Indicators\AtrFilter.mqh    ATR com sentinela -1.0 (sem leitura)
  Monitoring\DiagGate.mqh     anti-repeticao de log (chave symbol|tag)
  Monitoring\Logger.mqh       log com prefixo
  Docs\README_<NAME>.md       o que e, como compilar, o que falta
  AGENTS.md                   contrato para o proximo agente

Nao gera .mqproj: o MetaEditor cria-o em Ficheiro > Novo > Expert Advisor.
Nao coloca ordens: InpEnableTrading=false e a execucao e um stub explicito.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
# ...\MQL5\Files\XAU_AI_PRO\Tools\new_mq5_project.py -> parents[3] = MQL5
MQL5_DIR = HERE.parents[3]
EXPERTS_DIR = MQL5_DIR / "Experts"

NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{1,31}$")

# --------------------------------------------------------------------------
# Templates MQL5.  O token __NAME__ e substituido pelo nome do projecto.
# Nao usar .format()/f-string: o codigo MQL5 esta cheio de { }.
# --------------------------------------------------------------------------

TPL_CONFIG = r"""//+------------------------------------------------------------------+
//| Config.mqh -- constantes e utilitarios de __NAME__
//| Gerado por new_mq5_project.py -- pode editar a vontade.
//+------------------------------------------------------------------+
#ifndef __NAME___CONFIG_MQH
#define __NAME___CONFIG_MQH

#define APP_NAME    "__NAME__"
#define APP_VERSION "1.0.0"

// Normaliza o volume ao step / min / max do simbolo.
double ConfigNormalizeVolume(const string symbol, const double volume)
{
   double vmin  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double vmax  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(vstep <= 0.0) vstep = 0.01;
   if(vmin  <= 0.0) vmin  = vstep;
   if(vmax  <= 0.0) vmax  = vmin;

   double v = MathFloor(volume / vstep + 0.5) * vstep;
   if(v < vmin) v = vmin;
   if(v > vmax) v = vmax;
   return NormalizeDouble(v, 2);
}

// Distancia de um preco em "pontos" do simbolo (inteiro, para logs).
int ConfigPoints(const string symbol, const double priceDistance)
{
   const double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   if(point <= 0.0) return 0;
   return (int)MathRound(priceDistance / point);
}

#endif // __NAME___CONFIG_MQH
"""

TPL_DIAGGATE = r"""//+------------------------------------------------------------------+
//| DiagGate.mqh -- impede que a mesma linha de journal se repita
//| dentro de uma janela. Chave = symbol|tag, desfecho = outcome.
//| Uso:  if(DiagGateAllow(_Symbol,"ai_stale","VENCIDA",900)) Print(...);
//| Regra: o gate abafa o RUIDO, nunca esconde um desfecho NOVO.
//+------------------------------------------------------------------+
#ifndef DIAGGATE_MQH
#define DIAGGATE_MQH

#define DIAG_GATE_WINDOW_DEFAULT 300   // segundos
#define DIAG_GATE_MAX_KEYS       64    // chaves simultaneas

string   g_dgKey[DIAG_GATE_MAX_KEYS];
string   g_dgOutcome[DIAG_GATE_MAX_KEYS];
datetime g_dgTime[DIAG_GATE_MAX_KEYS];
int      g_dgCount = 0;

// true  -> pode imprimir (primeira vez, desfecho novo, ou janela vencida)
// false -> repeticao identica dentro da janela: suprimir
bool DiagGateAllow(const string symbol, const string tag,
                   const string outcome, const int heartbeatSec = 0)
{
   const string   key    = symbol + "|" + tag;
   const datetime now    = (datetime)TimeLocal();   // TimeCurrent() congela com mercado fechado
   const long     janela = (heartbeatSec > 0 ? (long)heartbeatSec : (long)DIAG_GATE_WINDOW_DEFAULT);

   for(int i = 0; i < g_dgCount; i++)
   {
      if(g_dgKey[i] != key) continue;
      const long dt = (long)(now - g_dgTime[i]);
      if(dt < janela && g_dgOutcome[i] == outcome) return false;
      g_dgOutcome[i] = outcome;
      g_dgTime[i]    = now;
      return true;
   }

   if(g_dgCount < DIAG_GATE_MAX_KEYS)
   {
      g_dgKey[g_dgCount]     = key;
      g_dgOutcome[g_dgCount] = outcome;
      g_dgTime[g_dgCount]    = now;
      g_dgCount++;
   }
   return true;
}

int  DiagGateActiveKeys(void) { return g_dgCount; }
void DiagGateReset(void)      { g_dgCount = 0; }

#endif // DIAGGATE_MQH
"""

TPL_LOGGER = r"""//+------------------------------------------------------------------+
//| Logger.mqh -- log com prefixo unico. Nao filtra nada:
//| filtrar e trabalho do DiagGate, nao do Logger.
//+------------------------------------------------------------------+
#ifndef LOGGER_MQH
#define LOGGER_MQH

void LogInfo(const string tag, const string msg) { Print("[", tag, "] ", msg); }
void LogWarn(const string tag, const string msg) { Print("[", tag, "] AVISO | ", msg); }
void LogErr (const string tag, const string msg) { Print("[", tag, "] ERRO | ", msg); }

string LogNum(const double value, const int digits = 2)
{
   return DoubleToString(value, digits);
}

#endif // LOGGER_MQH
"""

TPL_ATR = r"""//+------------------------------------------------------------------+
//| AtrFilter.mqh -- ATR com sentinela explicita.
//| Regra do projecto: -1.0 significa "sem leitura" (fail-open no
//| chamador). Nunca devolver 0.0, porque 0.0 e um valor valido e
//| esconde o aquecimento do indicador.
//+------------------------------------------------------------------+
#ifndef ATRFILTER_MQH
#define ATRFILTER_MQH

int g_atrHandle = INVALID_HANDLE;

bool AtrInit(const string symbol, const int period)
{
   g_atrHandle = iATR(symbol, PERIOD_CURRENT, period);
   return (g_atrHandle != INVALID_HANDLE);
}

// -1.0 = sem leitura. shift=1 usa a barra fechada (nao repinta).
double AtrRead(const int shift = 1)
{
   if(g_atrHandle == INVALID_HANDLE) return -1.0;
   double buf[];
   if(CopyBuffer(g_atrHandle, 0, shift, 1, buf) != 1) return -1.0;
   if(buf[0] <= 0.0) return -1.0;
   return buf[0];
}

void AtrRelease(void)
{
   if(g_atrHandle != INVALID_HANDLE)
   {
      IndicatorRelease(g_atrHandle);
      g_atrHandle = INVALID_HANDLE;
   }
}

#endif // ATRFILTER_MQH
"""

TPL_SESSION = r"""//+------------------------------------------------------------------+
//| SessionFilter.mqh -- janela horaria do servidor.
//| start == end  -> 24 horas (nao bloqueia).
//+------------------------------------------------------------------+
#ifndef SESSIONFILTER_MQH
#define SESSIONFILTER_MQH

bool SessionAllows(const int startHour, const int endHour)
{
   if(startHour == endHour) return true;

   MqlDateTime st;
   TimeToStruct(TimeCurrent(), st);

   if(startHour < endHour)
      return (st.hour >= startHour && st.hour < endHour);

   // janela que atravessa a meia-noite (ex.: 22 -> 6)
   return (st.hour >= startHour || st.hour < endHour);
}

#endif // SESSIONFILTER_MQH
"""

TPL_RISK = r"""//+------------------------------------------------------------------+
//| RiskCenter.mqh -- o unico sitio que decide "pode operar?".
//| Tres travas: risco por trade, perda diaria, drawdown desde o pico.
//| Devolve false com motivo escrito em RiskCenterReason().
//+------------------------------------------------------------------+
#ifndef RISKCENTER_MQH
#define RISKCENTER_MQH

#include "Config.mqh"

double   g_rcPeakEquity      = 0.0;
double   g_rcDayStartEquity  = 0.0;
datetime g_rcDayStamp        = 0;
string   g_rcReason          = "";

string RiskCenterReason(void) { return g_rcReason; }

// Reinicia a referencia de "inicio do dia" quando muda a data do servidor.
void RiskCenterResetDay(void)
{
   MqlDateTime st;
   TimeToStruct(TimeCurrent(), st);
   st.hour = 0; st.min = 0; st.sec = 0;
   const datetime today = StructToTime(st);

   if(today == g_rcDayStamp) return;
   g_rcDayStamp       = today;
   g_rcDayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
}

// stopDistance em unidades de PRECO (ex.: atr * 2.0), nao em pontos.
bool RiskCenterAllows(const string symbol,
                      const double riskPercent,
                      const double stopDistance,
                      const double maxDailyLossPercent,
                      const double maxDrawdownPercent,
                      double &outVolume)
{
   outVolume  = 0.0;
   g_rcReason = "";

   const double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
   {
      g_rcReason = "equity invalida";
      return false;
   }

   RiskCenterResetDay();
   if(g_rcPeakEquity <= 0.0 || equity > g_rcPeakEquity) g_rcPeakEquity = equity;

   if(maxDailyLossPercent > 0.0 && g_rcDayStartEquity > 0.0)
   {
      const double perdaDia = (g_rcDayStartEquity - equity) / g_rcDayStartEquity * 100.0;
      if(perdaDia >= maxDailyLossPercent)
      {
         g_rcReason = "perda diaria " + LogNum(perdaDia) + "% >= limite " + LogNum(maxDailyLossPercent) + "%";
         return false;
      }
   }

   if(maxDrawdownPercent > 0.0 && g_rcPeakEquity > 0.0)
   {
      const double dd = (g_rcPeakEquity - equity) / g_rcPeakEquity * 100.0;
      if(dd >= maxDrawdownPercent)
      {
         g_rcReason = "drawdown " + LogNum(dd) + "% >= limite " + LogNum(maxDrawdownPercent) + "%";
         return false;
      }
   }

   const double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   const double tickSize  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0 || stopDistance <= 0.0)
   {
      g_rcReason = "parametros de risco invalidos (tickValue/tickSize/stop)";
      return false;
   }

   const double riscoDinheiro = equity * riskPercent / 100.0;
   const double perdaPorLote  = (stopDistance / tickSize) * tickValue;
   if(perdaPorLote <= 0.0)
   {
      g_rcReason = "perda por lote invalida";
      return false;
   }

   outVolume = ConfigNormalizeVolume(symbol, riscoDinheiro / perdaPorLote);
   if(outVolume <= 0.0)
   {
      g_rcReason = "volume calculado <= 0";
      return false;
   }
   return true;
}

#endif // RISKCENTER_MQH
"""

TPL_EA = r"""//+------------------------------------------------------------------+
//| __NAME__.mq5 -- esqueleto modular gerado por new_mq5_project.py
//| Fluxo: barra nova -> ATR -> sessao -> risco -> sinal -> execucao
//| A execucao esta DESLIGADA (InpEnableTrading=false) e o sinal e
//| um stub explicito: nenhuma ordem sai daqui sem codigo seu.
//+------------------------------------------------------------------+
#property copyright   "MetaTrader Assistant"
#property version     "1.00"
#property description "Esqueleto modular __NAME__: sinal -> risco -> execucao desligada."

#include <Trade\Trade.mqh>
#include "Core\Config.mqh"
#include "Monitoring\Logger.mqh"
#include "Monitoring\DiagGate.mqh"
#include "Indicators\AtrFilter.mqh"
#include "Filters\SessionFilter.mqh"
#include "Core\RiskCenter.mqh"

input group "Risco"
input double InpRiskPercent         = 0.5;    // Risco por trade (% do equity)
input double InpMaxDailyLossPercent = 3.0;    // Perda diaria maxima (%)
input double InpMaxDrawdownPercent  = 10.0;   // Drawdown maximo desde o pico (%)
input double InpStopAtrMult         = 2.0;    // Stop = ATR * multiplo
input int    InpAtrPeriod           = 14;     // Periodo do ATR

input group "Execucao"
input long   InpMagic               = 2026001; // Magic number
input bool   InpEnableTrading       = false;   // Ligar execucao real (por omissao DESLIGADA)
input bool   InpVerbose             = true;    // Log detalhado (com gate)

input group "Sessao"
input int    InpStartHour           = 0;       // Hora inicial (servidor)
input int    InpEndHour             = 0;       // Hora final (0 = 24h)

CTrade   g_trade;
datetime g_lastBar  = 0;
int      g_barsSeen = 0;
int      g_blocks   = 0;

//--- declarada antes de OnInit: o compilador MQL5 nao gosta de adivinhar
int InitFail(const string why)
{
   LogErr("INIT", why);
   return INIT_PARAMETERS_INCORRECT;
}

int OnInit()
{
   if(InpMagic <= 0)                                 return InitFail("InpMagic deve ser > 0");
   if(InpRiskPercent <= 0.0 || InpRiskPercent > 5.0)  return InitFail("InpRiskPercent fora da faixa 0..5");
   if(InpMaxDailyLossPercent < 0.0)                   return InitFail("InpMaxDailyLossPercent negativo");
   if(InpMaxDrawdownPercent < 0.0)                    return InitFail("InpMaxDrawdownPercent negativo");
   if(InpAtrPeriod < 2)                               return InitFail("InpAtrPeriod < 2");
   if(!AtrInit(_Symbol, InpAtrPeriod))                return InitFail("falha ao criar o handle do ATR");

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(20);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   LogInfo("INIT", APP_NAME + " v" + APP_VERSION +
           " | " + _Symbol + " " + EnumToString(_Period) +
           " | magic=" + IntegerToString(InpMagic) +
           " | trading=" + (InpEnableTrading ? "LIGADO" : "DESLIGADO"));
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   AtrRelease();
   LogInfo("FIM", "motivo=" + IntegerToString(reason) +
           " | barras=" + IntegerToString(g_barsSeen) +
           " | bloqueios=" + IntegerToString(g_blocks) +
           " | chaves_gate=" + IntegerToString(DiagGateActiveKeys()));
}

// 0 = sem sinal, +1 = compra, -1 = venda. SUBSTITUA por a sua logica.
int SignalStub(void)
{
   return 0;
}

void OnTick()
{
   const datetime bar = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(bar == 0)      return;          // historico ainda a carregar
   if(bar == g_lastBar) return;       // so uma decisao por barra
   g_lastBar = bar;
   g_barsSeen++;

   const double atr = AtrRead(1);
   if(atr < 0.0)
   {
      g_blocks++;
      if(DiagGateAllow(_Symbol, "atr", "SEM_LEITURA", 600))
         LogWarn("ATR", "sem leitura (aquecimento) -- fail-open no filtro");
      return;
   }

   if(!SessionAllows(InpStartHour, InpEndHour))
   {
      g_blocks++;
      if(DiagGateAllow(_Symbol, "sessao", "FORA", 900))
         LogInfo("SESSAO", "fora da janela " + IntegerToString(InpStartHour) + ".." + IntegerToString(InpEndHour));
      return;
   }

   const double stopDistance = atr * InpStopAtrMult;
   double volume = 0.0;
   if(!RiskCenterAllows(_Symbol, InpRiskPercent, stopDistance,
                        InpMaxDailyLossPercent, InpMaxDrawdownPercent, volume))
   {
      g_blocks++;
      if(DiagGateAllow(_Symbol, "risco", RiskCenterReason(), 300))
         LogWarn("RISCO", RiskCenterReason());
      return;
   }

   if(InpVerbose && DiagGateAllow(_Symbol, "ciclo", "OK", 900))
      LogInfo("CICLO", "bar=" + TimeToString(bar, TIME_DATE | TIME_MINUTES) +
              " | atr=" + LogNum(atr, 5) +
              " | stop=" + LogNum(stopDistance, 5) +
              " | vol=" + LogNum(volume, 2));

   const int sinal = SignalStub();
   if(sinal == 0) return;

   if(!InpEnableTrading)
   {
      g_blocks++;
      if(DiagGateAllow(_Symbol, "exec", "DESLIGADA", 900))
         LogInfo("EXEC", "sinal existe mas InpEnableTrading=false (esqueleto seguro)");
      return;
   }

   //--- AQUI entra a execucao real. Obrigatorio:
   //    1) g_trade.Buy/Sell(...)  2) ler ResultRetcode()
   //    3) 10009 (TRADE_RETCODE_DONE) ou tratar o erro
   //    4) SL != 0 e TP coerentes com o lado da ordem
   if(DiagGateAllow(_Symbol, "exec", "STUB", 900))
      LogWarn("EXEC", "execucao nao implementada neste esqueleto (sinal=" + IntegerToString(sinal) + ")");
}
//+------------------------------------------------------------------+
"""

TPL_README = r"""# __NAME__

Projecto MQL5 gerado por `new_mq5_project.py` em __DATE__.

## O que ja existe

| Ficheiro | Responsabilidade |
|---|---|
| `__NAME__.mq5` | entrada: `OnInit` / `OnTick` / `OnDeinit`; so orquestra |
| `Core/Config.mqh` | constantes e normalizacao de volume |
| `Core/RiskCenter.mqh` | risco por trade, perda diaria, drawdown |
| `Filters/SessionFilter.mqh` | janela horaria |
| `Indicators/AtrFilter.mqh` | ATR com sentinela `-1.0` |
| `Monitoring/DiagGate.mqh` | anti-repeticao de journal |
| `Monitoring/Logger.mqh` | log com prefixo |

## O que NAO existe (por desenho)

- **execucao real**: `InpEnableTrading=false` e `SignalStub()` devolve 0;
- **sinal**: nao ha estrategia nenhuma aqui;
- **`.mqproj`**: crie em MetaEditor > Ficheiro > Novo > Expert Advisor, ou
  abra o `.mq5` directamente (compila na mesma).

## Ordem de trabalho recomendada

1. Compilar assim como esta e confirmar **0 errors, 0 warnings**.
2. Escrever o sinal em `SignalStub()` (uma funcao, testavel isolada).
3. So depois ligar a execucao, com `ResultRetcode()` verificado.
4. Cada linha de log nova passa por `DiagGateAllow(...)`.
5. Antes de ligar dinheiro real: backtest + forward test em demo.

## Seguranca

- `InpRiskPercent` acima de 5 % e recusado no `OnInit`.
- Sem `Stop Loss` calculado nao ha volume (`RiskCenterAllows` devolve false).
- `magic` obrigatorio e diferente de zero.
"""

TPL_AGENTS = r"""# AGENTS.md -- __NAME__

Contrato para qualquer agente que trabalhe neste projecto.

## Pre-flight obrigatorio

1. `get_workspace_info` nos MCP disponiveis (metaeditor5, metatrader5).
2. Dizer as raizes em que se vai trabalhar.
3. So depois tocar em codigo.

## Regras

1. Nenhuma mudanca termina sem compilacao **0 errors / 0 warnings**.
2. Toda a mudanca traz numero: antes -> depois.
3. `.ex5` mais recente que `.mq5`, senao o binario em vigor e o antigo.
4. Compilar nao reanexa: o EA novo so entra em vigor ao reanexar ao grafico.
5. Nao alterar `InpRiskPercent`, `InpMaxDailyLossPercent`,
   `InpMaxDrawdownPercent` sem justificacao escrita.
6. Log novo passa por `DiagGateAllow(symbol, tag, outcome, heartbeatSec)`.
7. Sentinela explicita para "sem leitura" (`-1.0`), nunca `0.0`.
8. Nada de `OrderSend` sem `ResultRetcode()` verificado.
9. Comentarios em portugues; identificadores e nomes de ficheiro em ingles.

## Estrutura

```
__NAME__/
  __NAME__.mq5
  Core/          Config, RiskCenter
  Filters/       SessionFilter
  Indicators/    AtrFilter
  Monitoring/    DiagGate, Logger
  Docs/          README___NAME__.md
```

## Ferramentas do dono

```
python.exe ..\..\Files\XAU_AI_PRO\Tools\audit_project.py "<pasta deste projecto>"
python.exe ..\..\Files\XAU_AI_PRO\Tools\new_mq5_project.py --list
```
"""

TEMPLATES: dict[str, str] = {
    "Core/Config.mqh": TPL_CONFIG,
    "Core/RiskCenter.mqh": TPL_RISK,
    "Filters/SessionFilter.mqh": TPL_SESSION,
    "Indicators/AtrFilter.mqh": TPL_ATR,
    "Monitoring/DiagGate.mqh": TPL_DIAGGATE,
    "Monitoring/Logger.mqh": TPL_LOGGER,
}

# ficheiros cujo nome depende do projecto: chave -> template
NAMED_TEMPLATES: dict[str, str] = {
    "__NAME__.mq5": TPL_EA,
    "Docs/README___NAME__.md": TPL_README,
    "AGENTS.md": TPL_AGENTS,
}


def render(template: str, name: str, date: str) -> str:
    """Substitui apenas os tokens conhecidos; nunca interpreta { } do MQL5."""
    return template.replace("__NAME__", name).replace("__DATE__", date)


def plan(name: str, root: Path) -> list[tuple[Path, str]]:
    project = root / name
    out: list[tuple[Path, str]] = []
    for rel, tpl in list(TEMPLATES.items()) + list(NAMED_TEMPLATES.items()):
        out.append((project / rel.replace("__NAME__", name), tpl))
    return out


def generate(name: str, root: Path, force: bool, date: str) -> tuple[int, int]:
    written = skipped = 0
    for path, tpl in plan(name, root):
        if path.exists() and not force:
            skipped += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        # newline="\r\n" nao existe; escrevemos bytes CRLF como o MetaEditor
        data = render(tpl, name, date).replace("\r\n", "\n").replace("\n", "\r\n")
        path.write_bytes(data.encode("utf-8"))
        written += 1
    return written, skipped


def selftest() -> int:
    import tempfile

    fails = 0
    total = 0

    def check(label: str, ok: bool) -> None:
        nonlocal fails, total
        total += 1
        print(("  OK   " if ok else "  FALHA") + " | " + label)
        if not ok:
            fails += 1

    check("nome valido aceite", bool(NAME_RE.match("MEU_EA")))
    check("nome minusculo recusado", not NAME_RE.match("meu_ea"))
    check("nome com hifen recusado", not NAME_RE.match("MEU-EA"))
    check("nome vazio recusado", not NAME_RE.match(""))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        written, skipped = generate("DEMO_EA", root, force=False, date="2026-01-01")
        check("gerou todos os ficheiros", written == len(TEMPLATES) + len(NAMED_TEMPLATES))
        check("nada ignorado na 1a vez", skipped == 0)
        ea = root / "DEMO_EA" / "DEMO_EA.mq5"
        check("entrada .mq5 existe", ea.is_file())
        text = ea.read_text(encoding="utf-8")
        check("token __NAME__ substituido", "__NAME__" not in text)
        check("execucao desligada por omissao", "InpEnableTrading       = false" in text)
        check("CRLF preservado", "\r\n" in ea.read_bytes().decode("utf-8"))
        _, skipped2 = generate("DEMO_EA", root, force=False, date="2026-01-01")
        check("segunda passagem nao sobrescreve", skipped2 == len(TEMPLATES) + len(NAMED_TEMPLATES))

    print("total=" + str(total) + " falhas=" + str(fails))
    return 0 if fails == 0 else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Gera um projecto MQL5 modular compilavel.")
    ap.add_argument("--name", help="nome do projecto (ex.: MEU_EA)")
    ap.add_argument("--root", default=str(EXPERTS_DIR), help="pasta onde criar <NAME>/")
    ap.add_argument("--force", action="store_true", help="sobrescrever ficheiros existentes")
    ap.add_argument("--date", default="", help="data a carimbar no README")
    ap.add_argument("--list", action="store_true", help="listar ficheiros gerados")
    ap.add_argument("--selftest", action="store_true", help="correr as provas internas")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.list:
        for rel in list(TEMPLATES.keys()) + list(NAMED_TEMPLATES.keys()):
            print(rel)
        print("total=" + str(len(TEMPLATES) + len(NAMED_TEMPLATES)) + " ficheiros")
        return 0

    if not args.name:
        ap.print_help()
        return 2
    if not NAME_RE.match(args.name):
        print("RECUSA: nome invalido '" + args.name + "' -- use Maiuscula inicial, A-Z a-z 0-9 _ (2..32)")
        return 2

    date = args.date or "data nao indicada"
    written, skipped = generate(args.name, Path(args.root), args.force, date)
    print("projecto  : " + str(Path(args.root) / args.name))
    print("escritos  : " + str(written))
    print("ignorados : " + str(skipped))
    print("proximo   : compilar " + args.name + ".mq5 e confirmar 0 errors / 0 warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
