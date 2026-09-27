# -*- coding: utf-8 -*-
"""Mapa do Expert Advisor XAU AI PRO para o copiloto.

POR QUE ISTO EXISTE
===================
O copiloto precisa responder sobre o EA com precisao. Se ele "inventar" um
controle de risco, o usuario perde tempo procurando algo que nao existe — e o
primeiro assistente deste projeto prometia coisa que nao existia. Este modulo
guarda o que foi VERIFICADO por leitura do codigo e pelos artefatos de runtime.

O QUE ESTE MAPA NAO E
======================
Nao e um resumo do codigo, e um indice de ONDE CADA COISA ESTA E O QUE ELA
FAZ (ou deixa de fazer). Os 50 achados da auditoria estao em ACHADOS, com
arquivo e linha, para que a resposta do copiloto seja citavel.

COMO FOI VERIFICADO
===================
- Leitura direta dos 119 arquivos .mq5/.mqh da arvore principal.
- Achados 2, 3, 9 e a ausencia de cabecalho no dataset foram confirmados
  contra os artefatos reais em MQL5/Files/Data/.
- Nada aqui foi inferido de documentacao: onde a documentacao contradiz o
  codigo, o codigo vence e a contradicao vira achado.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

# Raiz do repositorio.
RAIZ = Path(__file__).resolve().parent.parent
ARVORE_EA = RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO"
DADOS_RUNTIME = Path(
    os.getenv(
        "XAU_MT5_DATA",
        str(Path(os.environ.get("APPDATA", "")) / "MetaQuotes" / "Terminal"
            / "D0E8209F77C8CF37AD8BF550E51FF075" / "MQL5" / "Files" / "Data"),
    )
)


@dataclass(frozen=True)
class Achado:
    """Um problema verificado, com localizacao citavel."""

    id: int
    gravidade: str          # CRITICO | ALTO | MEDIO | BAIXO
    arquivo: str
    linha: str
    titulo: str
    descricao: str
    por_que_importa: str
    categoria: str = "geral"

    def para_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "gravidade": self.gravidade, "arquivo": self.arquivo,
            "linha": self.linha, "titulo": self.titulo, "descricao": self.descricao,
            "por_que_importa": self.por_que_importa, "categoria": self.categoria,
        }

    def referencia(self) -> str:
        return f"{self.arquivo}:{self.linha}"


# Os 10 mais graves, que sao a resposta padrao quando o usuario pergunta
# "qual o pior problema do EA".
ACHADOS_CRITICOS_PRINCIPAIS: list[Achado] = [
    Achado(1, "CRITICO", "Enterprise/OrderRetry.mqh", "606",
           "Retry de execucao inoperante em producao",
           "ExecLockAcquire() e chamado a cada iteracao do laco de retry. Na "
           "tentativa 0 adquire o lock; na tentativa 1 o GlobalVariableSetOnCondition "
           "falha (valor atual != 0.0) e o TTL de 5s nao vence, porque o Sleep e de "
           "100/200/400ms. A funcao retorna RETRY_INVALID com 'LOCK BUSY'. "
           "Resultado: nunca ha mais de 1 tentativa.",
           "Uma ordem que falha por REQUOTE/TIMEOUT/PRICE_CHANGED e abandonada na "
           "primeira falha. Pior: no Strategy Tester o lock e pulado (!sgTester), "
           "entao todo backtest e forward test mede um comportamento de execucao que "
           "a producao nao tem.",
           "execucao"),
    Achado(2, "CRITICO", "XAU_AI_PRO.mq5", "1138-1152",
           "Argumentos ATR e RSI trocados na auditoria",
           "A assinatura de AuditLogTrackEntry e (symbol, ticket, price, rsi, adx, "
           "atr, ...). A chamada passa GetATR(), GetADX(), GetRSI(). ATR cai na "
           "coluna RSI e RSI cai na coluna ATR.",
           "Confirmado no full_audit.csv real: RSI=0.00 e ATR=41.09073 (41 e um RSI, "
           "nao um ATR de NZDUSD). A trilha de auditoria — base de toda validacao "
           "forward/backtest e de qualquer re-treino — esta corrompida.",
           "auditoria"),
    Achado(3, "CRITICO", "AI/AIConnector.mqh", "343-347, 522",
           "Controle de staleness da IA nunca dispara",
           "O codigo extrai a chave 'timestamp_utc' e todo o bloco de staleness "
           "(linhas 519-563) esta dentro de if(jsonTimestampUTC != \"\"). O pipeline "
           "Python publica 'timestamp', nao 'timestamp_utc'.",
           "AI_IsStale permanece false para sempre, AI_AgeSeconds fica -1.0 e "
           "MaxPredictionAgeSec=900 e codigo morto. O system_status.json do terminal "
           "mostra 'age_seconds: -1, stale: true, available: false' permanentemente. "
           "O EA opera com predicao de idade arbitraria.",
           "ia"),
    Achado(4, "CRITICO", "XAU_AI_PRO.mq5", "845-851",
           "Input AutoTrade=false nao impede operacao",
           "O gate e 'if(false) { ... return; }' — codigo inalcancavel. O input "
           "AutoTrade existe em Config.mqh:8 mas nunca e consultado.",
           "Carregar o EA com AutoTrade=false opera normalmente. Nao existe "
           "kill-switch por input; o unico controle e o botao 'Algoritmos' do "
           "terminal (linha 834). O preset AUTOTRADE_ON.set e o texto do FASE_FINAL "
           "sao enganosos ao sugerir que o input controla algo.",
           "risco"),
    Achado(5, "ALTO", "Enterprise/SafetyManager.mqh", "434-459",
           "Exposicao total bloqueia a conta lucrativa",
           "exposurePct = MathAbs(floatingProfit)/balance*100 e comparado com "
           "max_total_exposure hardcoded em 10.0 (linha 147-148, nao vem de input).",
           "MathAbs faz o check bloquear novas entradas quando a conta esta "
           "altamente lucrativa — o oposto do pretendido. Se a intencao era "
           "exposicao notional, a implementacao mede P/L flutuante.",
           "risco"),
    Achado(6, "ALTO", "Enterprise/CircuitBreaker.mqh", "810-838",
           "SAFE_MODE expira por tempo sem reavaliar a causa",
           "Run() volta a CIRCUIT_NORMAL so por tempo (m_cooldown_seconds=300, "
           "linha 150), sem reavaliar a condicao que disparou.",
           "Um SAFE_MODE por 'High drawdown detected' (linha 789) limpa sozinho em 5 "
           "minutos com o drawdown intacto. CIRCUIT_LOCKED nunca e alcancado; "
           "CIRCUIT_WARNING nunca e atribuido; o overload CanTrade(symbol), que age "
           "sobre spread e falha de IA, nunca e chamado.",
           "risco"),
    Achado(7, "ALTO", "Enterprise/SmartExecution.mqh", "224, 292, 358",
           "Lote validado com a especificacao do simbolo do grafico",
           "CVolumeValidator::Init() e chamado em CSmartExecution::Init() sem "
           "argumento, portanto carrega _Symbol. NormalizeVolume/ValidateVolume sao "
           "chamados sem o simbolo da requisicao e EnsureSymbol(\"\") substitui por "
           "_Symbol (VolumeValidator.mqh:157-158).",
           "Com EnableMultiSymbol=true e 11 simbolos, o step/min/max de GOLD# e "
           "aplicado a USDJPY, EURUSD etc., produzindo lotes invalidos ou truncados "
           "silenciosamente.",
           "execucao"),
    Achado(8, "ALTO", "Core/PerformanceAnalyzer.mqh", "2-3",
           "Guard de include duplicado mata 670 linhas de metricas",
           "Core/PerformanceAnalyzer.mqh e Monitoring/PerformanceAnalyzer.mqh usam o "
           "mesmo guard PERFORMANCEANALYZER_MQH. O include do Core (mq5:114) compila "
           "primeiro; o do Monitoring (mq5:117) vira no-op.",
           "Morrem PerformanceSharpe, Sortino, UlcerIndex, Expectancy, "
           "RecoveryFactor, MaxDrawdown e ProfitFactor. O modulo de validacao "
           "quantitativa roda sobre numeros que nao alimentam nada. Pior: o stub "
           "vivo conta 'profit >= 0' como DERROTA (Core:42-46), inflando perdas.",
           "metricas"),
    Achado(9, "ALTO", "XAU_AI_PRO.mq5", "222-223",
           "Globais AIScore/AIConfidence nunca sao atribuidos",
           "As globais AIScore (222) e AIConfidence (223) sao apenas inicializadas "
           "em 0.0. O sistema real usa AI_Score/AI_Confidence de AIConnector.mqh:35-36.",
           "Toda telemetria de IA gravada (auditoria, forward test, backtest, "
           "benchmark) registra 0.00. mq5:1419 classifica toda trade como "
           "STRATEGY_TECHNICAL mesmo com EnableAIFilter=true, porque "
           "'AIConfidence > 0.0' nunca e verdade. O benchmark de estrategias e "
           "invalido por construcao.",
           "ia"),
    Achado(10, "ALTO", "Core/RiskCenter.mqh", "19-25, 125",
            "A fachada unica de risco documentada nao e chamada",
            "RiskAllowEntry nao tem nenhum chamador. RiskEvaluate so e invocada por "
            "Monitoring/SystemStatus.mqh:87, que e observabilidade.",
            "O header afirma que e a 'fachada unica de decisao de risco para NOVAS "
            "ENTRADAS, cada limite com um unico ponto de verificacao' — e falso. O "
            "gate real e uma sequencia informal, com brecha conhecida: "
            "ExecutionEngine.mqh:62-63 pula CalculateLotByRisk inteiro, e a gestao "
            "de posicoes envia ordens com CTrade cru, sem OrderCheck, retry ou lock.",
            "risco"),
]

# Os demais, por categoria. Registrados para o copiloto citar quando perguntado.
ACHADOS_ADICIONAIS: list[Achado] = [
    Achado(11, "ALTO", "AI/Dataset.mqh", "64, 96, 248, 447",
           "Subsistema de dataset 100% morto",
           "DatasetInit(), AddToDataset() e ExportDatasetCSV() nunca sao chamados. "
           "mq5:229 declara int DatasetIndex = -1, estado duplicado de Dataset.mqh:58, "
           "e nunca e atualizado.",
           "UpdateDatasetResult(-1, ...) retorna imediatamente. "
           "Data/trades_dataset.csv nunca e gerado, quebrando o ReplayDatasetFile.",
           "dados"),
    Achado(12, "ALTO", "Core/RiskEngine.mqh", "129",
           "Lote normalizado com 2 decimais fixos",
           "NormalizeDouble(lot, 2) ignora SYMBOL_VOLUME_STEP.",
           "Para step 0.001 o lote e truncado (0.029 -> 0.02); para step 1.0 pode "
           "ser zerado. Alem disso RiskEngine.mqh:28-29 devolve 0.01 fixo para "
           "symbol==\"\" — fail-open numa funcao de risco.",
           "risco"),
    Achado(13, "MEDIO", "Core/RiskEngine.mqh", "103-117",
           "AllowMinLotOverride=true por padrao",
           "Quando o lote calculado fica abaixo do minimo do broker, o EA forca o "
           "minimo e loga 'Risco real excede o configurado'.",
           "Com RiskPercent=1.0 e AllowMinLotOverride=true, o risco efetivo por trade "
           "e silenciosamente maior que 1%. Em conta pequena o minimo do broker "
           "domina. O modo estrito (false) e o nao-padrao.",
           "risco"),
    Achado(14, "MEDIO", "Enterprise/OrderRetry.mqh", "396-452, 573",
           "RecentFillExists e cega a direcao",
           "Compara so simbolo+magic+ENTRY_IN, e esta fora do laco de retry, "
           "contradizendo o comentario nas linhas 568-569.",
           "Um BUY-recem-preenchido suprime um SELL legitimo em menos de 8s. O "
           "caminho de supressao retorna RETRY_SUCCESS, entao ExecutionEngine "
           "chama RegisterTrade() e EventTradeApproved sem enviar ordem alguma, "
           "inflando o contador diario de trades do RiskHub.",
           "execucao"),
    Achado(15, "MEDIO", "Enterprise/SmartExecution.mqh", "909-928",
           "ModifyPosition envia OrderSend cru",
           "Sem OrderCheck, sem retry, sem lock atomico, sem AntiLoop, sem "
           "MQL_TRADE_ALLOWED, e so aceita TRADE_RETCODE_DONE.",
           "E um caminho de envio que burla a pilha de protecao. Nao tem chamador "
           "vivo no fluxo principal, mas existe como caminho alternativo.",
           "execucao"),
    Achado(16, "MEDIO", "Core/ExecutionEngine.mqh", "62-63",
           "Caminho que pula o calculo de lote por risco",
           "if(!UseRiskManagement && LotSize>0.0) lot=LotSize; dispensa "
           "CalculateLotByRisk inteiro.",
           "Sem MinEquityPercent, sem verificacao de perda diaria, sem escalonamento "
           "por drawdown. So sobrevivem CanTradeToday e CanOpenPosition.",
           "risco"),
    Achado(17, "MEDIO", "XAU_AI_PRO.mq5", "521-525",
           "DailyProfit recebe P/L flutuante",
           "Usa ACCOUNT_PROFIT, nao P/L realizado, apesar do comentario nas linhas "
           "507-519 dizer que o problema era double-counting.",
           "Alimenta PerformanceSave() e o relatorio diario de Telegram como se fosse "
           "resultado do dia. Ha ainda tres contadores de trades independentes.",
           "metricas"),
    Achado(18, "MEDIO", "XAU_AI_PRO.mq5", "1240-1249",
           "Break-even contado como derrota",
           "profit == 0 (break-even ou comissao) incrementa ConsecutiveLosses e "
           "PA_Losses.",
           "Distorce win-rate, streaks e ConsecutiveLosses — que alimenta a "
           "histerese do FailSafe.",
           "metricas"),
    Achado(19, "MEDIO", "Enterprise/CircuitBreaker.mqh", "858-913",
           "Circuit breaker nao bloqueia por spread nem por falha de IA",
           "RunSymbol() apenas imprime o resultado de CheckSpreadExplosion e "
           "CheckAIFailure. O overload CanTrade(string symbol), que age sobre os "
           "tres, nunca e chamado.",
           "O header do modulo afirma o contrario. Na pratica e essencialmente so um "
           "detetor de desconexao.",
           "risco"),
    Achado(20, "MEDIO", "Indicators/VolatilityFilter.mqh", "27-53",
           "InitATR nunca faz ArrayResize e copia tamanhos diferentes",
           "GetATR() copia 3 valores (linha 73) e HighVolatility() copia 20 "
           "(linha 251) para o mesmo buffer. Usa #define VOLATILITY_ATR_PERIOD 14 "
           "em vez do input ATRPeriod.",
           "Ha dois periodos de ATR no sistema, e um deles ignora o input. "
           "CircuitBreaker.mqh:497/576 usa ATRPeriod.",
           "indicadores"),
    Achado(21, "MEDIO", "Enterprise/SafetyManager.mqh", "503-521",
           "Risco por simbolo e por sessao sao stubs",
           "CheckRiskPerSymbol() e CheckRiskPerSession() sao 'return true;' com "
           "comentario 'Reservado para integracao'. CheckAll() chama ambos e reporta OK.",
           "SafetyLimits.max_risk_per_symbol=2.0 e max_risk_per_session=5.0 nunca sao "
           "lidos. Risco por simbolo e por sessao nao existe.",
           "risco"),
    Achado(22, "MEDIO", "AI/ModelGovernance.mqh", "51-69",
           "Governanca de modelo e decorativa",
           "ModelGovernanceRefresh() roda no OnInit antes de qualquer "
           "LoadAIPrediction, entao todos os campos vem vazios e g_modelGoverned "
           "permanece false. ModelProductionReady() retorna true por fail-open.",
           "O header promete exigir MODEL_ID/VERSION/DATASET_VERSION/STATUS=production "
           "para uso em producao. Nenhum gate consulta isso.",
           "ia"),
    Achado(23, "MEDIO", "Enterprise/Scheduler.mqh", "57-73",
           "Scheduler nunca recebe tarefas",
           "CScheduler::AddTask() nunca e chamado, logo ha 0 tarefas.",
           "EnableWeekendShutdown e SchedulerIntervalSec sao inputs sem referencia no "
           "codigo. O shutdown de fim de semana anunciado no Config.mqh:225 nao existe.",
           "geral"),
    Achado(24, "MEDIO", "Enterprise/CircuitBreaker.mqh", "346-394",
           "Tres definicoes diferentes de drawdown com o mesmo input",
           "CheckHighDrawdown usa (balance-equity)/balance; GetDrawdownPercent usa "
           "(peak_diario-equity)/peak; m_limits.max_daily_drawdown recebe "
           "MaxDailyLossPercent (5%) enquanto RiskEngine escala com "
           "MaxDrawdownPercent (15%).",
           "Tres semanticas, dois inputs, um nome. O comentario na linha 364-365 admite "
           "a divergencia sem resolve-la.",
           "risco"),
    Achado(25, "MEDIO", "Enterprise/AdaptiveWeights.mqh", "76-175",
           "Pesos 'adaptativos' sao constantes",
           "AdjustWeights() nunca e chamado. Os pesos sao 0.30/0.25/0.20/0.15/0.10 "
           "(linhas 18-25) e nao se adaptam a nada.",
           "AILearningMemory::GetLearningWeight() tambem nunca e usada no score — so "
           "MemoryBoost().",
           "ia"),
    Achado(26, "MEDIO", "XAU_AI_PRO.mq5", "1042-1046",
           "Vazamento de GlobalVariables sem limite",
           "XAI_PRO_DEAL_<ticket> cria uma GV por deal, para sempre. "
           "XAI_PRO_SENT_<sym>_<type> tambem. O cleanup de MarkTradedBar so varre o "
           "prefixo XAI_PRO_LATCH_<sym>_.",
           "Em operacao longa o GlobalVariablesTotal() cresce sem limite, e "
           "MarkTradedBar itera todas as GVs a cada nova vela (custo O(total)).",
           "geral"),
    Achado(27, "MEDIO", "Enterprise/OrderRetry.mqh", "241-246",
           "TRADE_RETCODE_NO_CHANGES tratado como sucesso",
           "Esta em IsSuccessRetcode e em nenhum IsInvalidRetcode.",
           "O broker respondeu 'requisicao identica, nada a fazer' — nao houve fill. "
           "O fluxo conta EXEC_SUCCESS, RegisterTrade(), EventTradeApproved e marca o "
           "latch da vela: a vela e perdida e o dia conta como trade executado.",
           "execucao"),
    Achado(28, "MEDIO", "Monitoring/HealthMonitor.mqh", "223-235",
           "Watchdog inerte por construcao",
           "HealthMonitorHeartbeat e chamado incondicionalmente a cada tick, no mesmo "
           "OnTick que executaria o modulo.",
           "g_wdLastTime sempre avanca e a verificacao nunca falha. Nenhum indicador "
           "morto e detectado. HealthIsHealthy() nao e usada em nenhum gate.",
           "saude"),
    Achado(29, "MEDIO", "Enterprise/RecoveryManager.mqh", "317-320",
           "Quatro verificacoes de disponibilidade de IA, tres com fail-open",
           "CheckJSON() e literalmente 'return CheckAI();'. Ambas com "
           "RequireAIJSON=false padrao retornando true incondicionalmente.",
           "Somadas a CircuitBreaker::CheckAIFailure e FailureMode::CheckAICoreAvailable, "
           "sao 4 verificacoes, 3 delas sem condicao. E todas usam _Symbol, irrelevante "
           "num pipeline multi-simbolo.",
           "saude"),
    Achado(30, "MEDIO", "AI/DataLogger.mqh", "201",
           "dataset.csv gravado sem cabecalho",
           "DataLoggerInit so escreve header if(FileSize(dataFile)==0).",
           "O arquivo real comeca direto com dado. O pipeline Python (data_engine_xau.py) "
           "le colunas por nome, com fallback de posicao fixa.",
           "dados"),
    Achado(31, "MEDIO", "XAU_AI_PRO.mq5", "634-656",
           "ProcessClosedTrades morta e perigosa",
           "Funcao sem chamador cujo header documenta que ela 'reprocessava as ultimas "
           "24h a cada tick, somando o mesmo profit multiplas vezes'.",
           "Se alguem religar, reintroduz o bug documentado. HistorySelect numa conta "
           "com historico denso e O(n) por chamada.",
           "dados"),
    Achado(32, "MEDIO", "XAU_AI_PRO.mq5", "554-561",
           "Duas fontes de verdade para 'posso operar?'",
           "CheckTradingConditions() e UpdateSafety() sao mortas. O OnTick reimplementa "
           "os mesmos 4 checks nas linhas 834, 889, 900, 872.",
           "A funcao agregadora esta desligada e a logica esta duplicada inline.",
           "risco"),
    Achado(33, "MEDIO", "Enterprise/BrokerAnalyzer.mqh", "157-193",
           "Slippage e filling calculados do simbolo errado",
           "m_cfg e inicializada so para _Symbol; EnsureSymbol/LoadSymbol nunca sao "
           "re-chamados. Ha ainda calculo duplicado de recommended_slippage "
           "(linhas 162-166 e 189-193).",
           "request.deviation e type_filling para EURUSD sao calculados do spread e "
           "digits de GOLD#. FOK tem prioridade sobre IOC, o mais agressivo.",
           "execucao"),
    Achado(34, "MEDIO", "Enterprise/ExecutionStats.mqh", "100-106",
           "avg_score nunca e atribuido e UpdateAfterTrade soma dinheiro a score",
           "RecordOrder so atribui avg_slippage e avg_delay_ms; m_stats.avg_score "
           "fica 0. UpdateAfterTrade soma profit a m_total_score, misturando unidades.",
           "GetSummary sempre imprime AvgScore=0.00. QuantValidator consome esses campos.",
           "metricas"),
    Achado(35, "BAIXO", "Monitoring/SystemStatus.mqh", "148",
           "age <= 900.0 hardcoded no snapshot",
           "Ignora o input MaxPredictionAgeSec. Como AI_AgeSeconds fica -1.0, "
           "predictions_available e sempre false.",
           "Mudar o input nao muda o corte, e o app consome um campo permanentemente falso.",
           "saude"),
    Achado(36, "BAIXO", "Monitoring/SystemStatus.mqh", "70",
           "P/L da conta inteira atribuido ao simbolo",
           "SSTradingSection reporta AccountInfoDouble(ACCOUNT_PROFIT) como se fosse o "
           "P/L de symbol.",
           "Atribuicao incorreta no snapshot que o app consome.",
           "saude"),
    Achado(37, "BAIXO", "XAU_AI_PRO.mq5", "197-260",
           "Bloco de estado do sistema majoritariamente decorativo",
           "UltimoOrderTicket, LastPositionTicket, LastBar, SafeMode, RecoveryRunning, "
           "ExecutionReady, VerboseMode, AIReady, AIStatus, TradingEnabled e outros "
           "sao declarados e nunca lidos ou escritos.",
           "Da a impressao de um painel de estado com muito mais informacao do que a "
           "que existe de fato.",
           "geral"),
    Achado(38, "BAIXO", "AI/AIEngine.mqh", "26, 85",
           "Tres funcoes chamadas GetAIConfidence",
           "AIClient.mqh:123 (int), AIEngine.mqh:85 (int, string=\"\") e "
           "AIConnector.mqh:911 (void). AIEngine.mqh:26 redeclara como prototype a "
           "funcao que AIClient ja define com assinatura diferente.",
           "Chamada com 1 argumento resolve para a versao do AIClient, que e fallback "
           "puramente local sem JSON — silenciosamente diferente do pretendido.",
           "ia"),
    Achado(39, "BAIXO", "Indicators/RSI.mqh", "73",
           "RSI exatamente 100 tratado como erro",
           "if(buffer[0] <= 0.0 || buffer[0] >= 100.0) return 0.0;",
           "RSI 100 e sobrecompra extrema, valor legitimo. Em tendencia forte o filtro "
           "retorna 0 e o bonus de qualidade se perde.",
           "indicadores"),
    Achado(40, "BAIXO", "Filters/SessionFilter.mqh", "11-31",
           "TradeEndHour=24 torna a condicao sempre verdadeira",
           "tm.hour < 24 e sempre verdade com o padrao; EnableSessionFilter=false por "
           "padrao. mq5:1147 usa IsTradingSession() como campo Session da auditoria.",
           "O campo Session da auditoria e sempre 'OPEN'. Alem disso usa "
           "TimeCurrent() (hora do servidor) enquanto o staleness usa TimeGMT().",
           "risco"),
    Achado(41, "BAIXO", "Monitoring/AuditLog.mqh", "574",
           "Delimitador divergente e perda silenciosa",
           "full_audit.csv usa ';' contra ',' em todos os outros. AuditLogTrackEntry "
           "faz return sem registrar nada quando o buffer de 1000 esta cheio e o "
           "flush falha.",
           "Com 11 instancias, ate 11.000 registros ficam so em RAM.",
           "auditoria"),
    Achado(42, "BAIXO", "Monitoring/QuantValidator.mqh", "271-288",
           "Escrita sem EventLock e relatorio so no OnDeinit",
           "Grava em FILE_COMMON com SEEK_END sem o EventLock que AuditLog e "
           "EventEmitter usam. QuantSaveReport() so e chamado no OnDeinit.",
           "Com 11 instancias ha interleave no quant_matrix.csv, e a matriz nunca e "
           "gerada durante a operacao.",
           "dados"),
]

TODOS_ACHADOS: list[Achado] = ACHADOS_CRITICOS_PRINCIPAIS + ACHADOS_ADICIONAIS

PESO_GRAVIDADE = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "BAIXO": 3}


# ----------------------------------------------------------------- inventario


@lru_cache(maxsize=1)
def _arvore() -> dict[str, Any]:
    """Lista os .mq5/.mqh com contagem de linhas. Cacheado por processo."""
    arquivos: list[dict[str, Any]] = []
    if not ARVORE_EA.exists():
        return {"existe": False, "arquivos": [], "total_linhas": 0, "total_arquivos": 0}
    for caminho in sorted(ARVORE_EA.rglob("*")):
        if not caminho.is_file() or caminho.suffix.lower() not in {".mq5", ".mqh"}:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(caminho.relative_to(ARVORE_EA)).replace("\\", "/")
        # Release/ e copia congelada da mesma arvore: nao conta como codigo vivo.
        vivo = not rel.startswith("Release/")
        arquivos.append({
            "arquivo": rel,
            "linhas": texto.count("\n") + 1,
            "bytes": caminho.stat().st_size,
            "vivo": vivo,
        })
    vivos = [a for a in arquivos if a["vivo"]]
    return {
        "existe": True,
        "arquivos": arquivos,
        "total_arquivos": len(vivos),
        "total_linhas": sum(a["linhas"] for a in vivos),
        "arquivos_vivos": vivos,
    }


def inventario() -> dict[str, Any]:
    """Estatisticas reais da arvore do EA."""
    arv = _arvore()
    if not arv["existe"]:
        return {
            "ok": False,
            "error": f"arvore do EA nao encontrada em {ARVORE_EA}",
            "achados": len(TODOS_ACHADOS),
        }
    principal = next((a for a in arv["arquivos"] if a["arquivo"] == "XAU_AI_PRO.mq5"), None)
    return {
        "ok": True,
        "raiz": str(ARVORE_EA),
        "total_arquivos": arv["total_arquivos"],
        "total_linhas": arv["total_linhas"],
        "arquivo_principal": principal,
        "ex5": _ex5_info(),
        "achados_por_gravidade": contar_gravidade(),
        "achados_por_categoria": contar_categoria(),
    }


def _ex5_info() -> dict[str, Any]:
    """Tamanho e data do binario compilado."""
    candidatos = [
        ARVORE_EA / "XAU_AI_PRO.ex5",
        RAIZ / "MQL5" / "Experts" / "XAU_AI_PRO" / "XAU_AI_PRO.ex5",
    ]
    for c in candidatos:
        if c.exists():
            st = c.stat()
            return {
                "caminho": str(c),
                "bytes": st.st_size,
                "modificado_em": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                # Um EA funcional rende centenas de KB a poucos MB. Abaixo de
                # 50 KB o binario provavelmente nao corresponde a esta fonte.
                "suspeito": st.st_size < 50_000,
            }
    return {"caminho": None, "bytes": None, "suspeito": False}


def contar_gravidade() -> dict[str, int]:
    contagem: dict[str, int] = {}
    for a in TODOS_ACHADOS:
        contagem[a.gravidade] = contagem.get(a.gravidade, 0) + 1
    return contagem


def contar_categoria() -> dict[str, int]:
    contagem: dict[str, int] = {}
    for a in TODOS_ACHADOS:
        contagem[a.categoria] = contagem.get(a.categoria, 0) + 1
    return contagem


# ------------------------------------------------------------- controles de risco


@dataclass(frozen=True)
class Controle:
    nome: str
    arquivo: str
    linha: str
    aplicado_em: str
    situacao: str          # ATIVO | PARCIAL | INOPERANTE | STUB
    detalhe: str = ""


CONTROLES_DE_RISCO: list[Controle] = [
    Controle("Perda diaria do dia", "Enterprise/SafetyManager.mqh", "302-327",
             "XAU_AI_PRO.mq5:889 + ExecutionEngine.mqh:52", "ATIVO"),
    Controle("Drawdown diario (peak via RiskHub)", "Enterprise/SafetyManager.mqh", "333-368",
             "XAU_AI_PRO.mq5:889", "PARCIAL", "Tres definicoes coexistem (achado 24)"),
    Controle("Drawdown de conta / emergency close", "Management/EquityProtection.mqh", "107-121",
             "XAU_AI_PRO.mq5:900", "ATIVO", "Chama EmergencyCloseAll()"),
    Controle("Escalonamento de lote por drawdown", "Core/RiskHub.mqh", "118",
             "ExecutionEngine.mqh:65", "ATIVO"),
    Controle("Maximo de posicoes abertas", "Core/PositionManager.mqh", "80-89",
             "MarketScanner.mqh:88 + ExecutionEngine.mqh:40", "ATIVO", "MaxOpenPositions=5"),
    Controle("Maximo de trades por dia", "Enterprise/SafetyManager.mqh", "374-394",
             "XAU_AI_PRO.mq5:889 + ExecutionEngine.mqh:52", "ATIVO", "MaxTradesPerDay=20"),
    Controle("Equity minima (% do balance)", "Core/RiskEngine.mqh", "38-44",
             "ExecutionEngine.mqh:65", "ATIVO"),
    Controle("Margem livre minima", "Enterprise/SafetyManager.mqh", "468-497",
             "XAU_AI_PRO.mq5:889", "ATIVO", "MinFreeMargin=20"),
    Controle("Margem da ordem (nivel 200%)", "Enterprise/MarginChecker.mqh", "42-56",
             "SmartExecution.mqh:365-374", "ATIVO"),
    Controle("Exposicao total", "Enterprise/SafetyManager.mqh", "400-462",
             "XAU_AI_PRO.mq5:889", "INOPERANTE",
             "MathAbs sobre P/L: bloqueia a conta lucrativa; limite 10% hardcoded"),
    Controle("Lote por risco calculado", "Core/RiskEngine.mqh", "80-129",
             "ExecutionEngine.mqh:59-69", "PARCIAL",
             "Ignora VOLUME_STEP; bypass em ExecutionEngine.mqh:62-63"),
    Controle("Volume dentro do spec do broker", "Enterprise/VolumeValidator.mqh", "176-229",
             "SmartExecution.mqh:291-298", "PARCIAL",
             "Usa o simbolo do grafico para todos (achado 7)"),
    Controle("Spread por simbolo", "Core/Config.mqh", "55-85",
             "ValidationEngine.mqh:90-122 + SmartExecution.mqh:330-345", "ATIVO"),
    Controle("Anti-loop (5 aberturas/60s)", "Enterprise/AntiLoop.mqh", "92-120",
             "SmartExecution.mqh:283-288", "ATIVO"),
    Controle("Latch 1 operacao por vela", "Core/MarketScanner.mqh", "29-51",
             "ProcessSymbol", "ATIVO"),
    Controle("Guard inter-instancia", "Enterprise/SmartExecution.mqh", "537-556",
             "OpenPosition", "ATIVO", "Unico ciente da direcao"),
    Controle("OrderCheck antes do envio", "Enterprise/OrderRetry.mqh", "644-663",
             "ExecuteWithRetry", "ATIVO"),
    Controle("Retry com backoff exponencial", "Enterprise/OrderRetry.mqh", "202-229",
             "ExecuteWithRetry", "INOPERANTE",
             "Lock re-adquirido no laco: nunca ha 2a tentativa (achado 1)"),
    Controle("Anti-duplicata por fill recente", "Enterprise/OrderRetry.mqh", "396-452",
             "ExecuteWithRetry", "PARCIAL", "Cega a direcao e fora do laco (achado 14)"),
    Controle("Lock atomico de envio", "Enterprise/OrderRetry.mqh", "479-515",
             "ExecuteWithRetry", "PARCIAL", "Quebra o proprio retry (achado 1)"),
    Controle("Simulacao pre-execucao", "Enterprise/SimulationEngine.mqh", "90-96",
             "ExecutionEngine.mqh:205", "ATIVO"),
    Controle("Circuit breaker", "Enterprise/CircuitBreaker.mqh", "750-839",
             "XAU_AI_PRO.mq5:870-877", "PARCIAL",
             "SAFE_MODE expira por tempo; nao bloqueia por spread nem IA (achados 6 e 19)"),
    Controle("Kill-switch por input AutoTrade", "XAU_AI_PRO.mq5", "845-851",
             "OnTick", "INOPERANTE", "if(false): codigo inalcancavel (achado 4)"),
    Controle("Risco por simbolo", "Enterprise/SafetyManager.mqh", "503-521",
             "CheckAll()", "STUB", "return true; reservado para integracao (achado 21)"),
    Controle("Risco por sessao", "Enterprise/SafetyManager.mqh", "503-521",
             "CheckAll()", "STUB", "return true; reservado para integracao (achado 21)"),
    Controle("Fachada unica de risco", "Core/RiskCenter.mqh", "19-25",
             "nenhum", "INOPERANTE", "RiskAllowEntry nao tem chamador (achado 10)"),
    Controle("Staleness da predicao de IA", "AI/AIConnector.mqh", "519-563",
             "LoadAIPrediction", "INOPERANTE", "Le 'timestamp_utc'; Python manda 'timestamp' (achado 3)"),
    Controle("Filtro de sessao de mercado", "Filters/SessionFilter.mqh", "11-31",
             "ValidationEngine", "PARCIAL", "TradeEndHour=24 torna a condicao sempre verdadeira"),
]


def controles_risco(situacao: str | None = None) -> list[dict[str, Any]]:
    sel = [c for c in CONTROLES_DE_RISCO if situacao is None or c.situacao == situacao]
    return [
        {"nome": c.nome, "arquivo": c.arquivo, "linha": c.linha,
         "aplicado_em": c.aplicado_em, "situacao": c.situacao, "detalhe": c.detalhe}
        for c in sel
    ]


# ------------------------------------------------------------------ fluxo


FLUXO_ON_TICK: list[dict[str, Any]] = [
    {"passo": 1, "linha": "769", "acao": "CTelemetry::RecordTick()"},
    {"passo": 2, "linha": "775-779", "acao": "if(!SystemInitialized) return;", "bloqueia": True},
    {"passo": 3, "linha": "784", "acao": "ForwardHeartbeat() (roda mesmo bloqueado)"},
    {"passo": 4, "linha": "793-800", "acao": "HealthMonitorUpdateTicks() + heartbeats"},
    {"passo": 5, "linha": "804-816", "acao": "HealthMonitorCheck()"},
    {"passo": 6, "linha": "818-827", "acao": "AI em UNAVAILABLE/ERROR/HOLD -> EventAIBlock", "bloqueia": False},
    {"passo": 7, "linha": "834-839", "acao": "MQL_TRADE_ALLOWED / TERMINAL_TRADE_ALLOWED", "bloqueia": True},
    {"passo": 8, "linha": "845-851", "acao": "if(false) — bloco AutoTrade morto", "bloqueia": False,
     "nota": "ACHEADO 4: AutoTrade=false nao impede nada"},
    {"passo": 9, "linha": "857-862", "acao": "SymbolsPending -> UpdateSymbolManager()", "bloqueia": True},
    {"passo": 10, "linha": "870", "acao": "CCircuitBreaker::Run()"},
    {"passo": 11, "linha": "872-877", "acao": "if(!CanTrade()) return;", "bloqueia": True},
    {"passo": 12, "linha": "883", "acao": "CRecoveryManager::Run() (throttle 30s)"},
    {"passo": 13, "linha": "889-894", "acao": "if(!CSafetyManager::CheckAll()) return;", "bloqueia": True,
     "nota": "Perda diaria, DD, trades, exposicao, margem"},
    {"passo": 14, "linha": "900-905", "acao": "if(!CheckEquityProtection()) return;", "bloqueia": True,
     "nota": "EmergencyCloseAll() se DD >= MaxDrawdownPercent"},
    {"passo": 15, "linha": "911", "acao": "UpdatePerformance()"},
    {"passo": 16, "linha": "917-920", "acao": "if(EnableAIFilter) UpdateAIStatus()"},
    {"passo": 17, "linha": "926", "acao": "datasetProgressed = UpdateDataset()"},
    {"passo": 18, "linha": "934-939", "acao": "HealthMonitorProgress()"},
    {"passo": 19, "linha": "948", "acao": "StateSet(STATE_MARKET_SCAN)"},
    {"passo": 20, "linha": "951-971",
     "acao": "Replay bloqueia OU ConnectionGuard OU FailureMode -> RunTradePipeline()",
     "bloqueia": False},
    {"passo": 21, "linha": "980", "acao": "ManagePositions() — RODA SEMPRE, fora de todos os returns",
     "nota": "Fechamento por stop/trailing/breakeven. Nao ha fechamento por sinal."},
    {"passo": 22, "linha": "986-996", "acao": "loop de posicoes -> StateSet(STATE_MANAGING)"},
    {"passo": 23, "linha": "1002", "acao": "UpdateDashboard()"},
]

CADEIA_DE_ENTRADA: list[dict[str, str]] = [
    {"passo": "1", "local": "MarketScanner.mqh:88", "acao": "CanOpenPosition — 1 posicao/simbolo + MaxOpenPositions"},
    {"passo": "2", "local": "MarketScanner.mqh:104-115", "acao": "Latch 1-decisao-por-vela (GlobalVariable)"},
    {"passo": "3", "local": "MarketScanner.mqh:128", "acao": "GetCombinedSignal — tecnico (SignalCore) + IA (AIEngine)"},
    {"passo": "4", "local": "DecisionEngine.mqh:376-488", "acao": "AllowTrade — spread, sessao, tendencia, ADX, regime, veto IA, MTF, noticias, score>=60"},
    {"passo": "5", "local": "ExecutionEngine.mqh:24-280", "acao": "ExecuteTrade — CanTrade (cooldown 10s), CanOpenPosition, CanTradeToday, CalculateLotByRisk"},
    {"passo": "6", "local": "OrderRetry.mqh:666", "acao": "OrderSend (via COrderRetry::ExecuteWithRetry)"},
    {"passo": "7", "local": "MarketScanner.mqh:220-221", "acao": "MarkTradedBar"},
]


# ------------------------------------------------------------------ busca


def buscar(termo: str, limite: int = 12) -> list[dict[str, Any]]:
    """Busca nos achados por titulo, descricao, arquivo ou categoria."""
    t = termo.strip().lower()
    if not t:
        return []
    achados: list[dict[str, Any]] = []
    for a in TODOS_ACHADOS:
        alvo = " ".join([a.titulo, a.descricao, a.por_que_importa, a.arquivo, a.categoria]).lower()
        if t in alvo:
            achados.append(a.para_dict())
    achados.sort(key=lambda d: (PESO_GRAVIDADE.get(d["gravidade"], 9), d["id"]))
    return achados[:limite]


def por_categoria(categoria: str) -> list[dict[str, Any]]:
    c = categoria.strip().lower()
    return [a.para_dict() for a in TODOS_ACHADOS if a.categoria == c]


def por_gravidade(gravidade: str) -> list[dict[str, Any]]:
    g = gravidade.strip().upper()
    return [a.para_dict() for a in TODOS_ACHADOS if a.gravidade == g]


# ------------------------------------------------------------------ runtime


def _ler_json(nome: str) -> dict[str, Any] | None:
    p = DADOS_RUNTIME / nome
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return None


def estado_runtime() -> dict[str, Any]:
    """O que o terminal esta reportando agora, dos arquivos reais."""
    status = _ler_json("system_status.json")
    predicoes: list[dict[str, Any]] = []
    try:
        for p in sorted(DADOS_RUNTIME.glob("prediction*.json")):
            d = _ler_json(p.name)
            if d:
                predicoes.append({
                    "arquivo": p.name,
                    "symbol": d.get("symbol"),
                    "signal": d.get("signal"),
                    "confidence": d.get("confidence"),
                    "available": d.get("available"),
                    "generated_at": d.get("generated_at") or d.get("timestamp"),
                })
    except OSError:
        pass
    return {
        "data_dir": str(DADOS_RUNTIME),
        "existe": DADOS_RUNTIME.exists(),
        "system_status": status,
        "predicoes": predicoes,
    }
