# -*- coding: utf-8 -*-
"""Pre-flight do XAU AI PRO: verifica o ambiente antes de qualquer operacao longa.

Por que existe
--------------
Os erros mais caros deste projeto nao aparecem no codigo: aparecem no meio de
uma operacao. O build do Android consumiu 3,4 GB e so entao o emulador avisou
"not enough space". Um `cmd.exe` de 344 KB na raiz ficou travado porque um
processo do Office o executava. Um script de limpeza aceitava array apenas
quando chamado via `-Command`, e falhava de forma opaca via `-File`.

Todas essas classes de erro sao detectaveis em segundos, antes de gastar
minutos. Este modulo e o ponto unico de verificacao: `python scripts/preflight.py`
imprime o relatorio e sai com codigo 1 se algo bloquear.

O que ele NAO faz
-----------------
Nao altera nada. Somente leitura: disco, ferramentas, portas, permissões,
estado do Git, guarda de MQL5 e presenca dos scripts bloqueados.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ===========================================================
# AUTORIZACOES DE ALTERACAO MQL5
# ===========================================================
# A guarda `checar_mql5()` reprova QUALQUER alteracao em `MQL5/Experts`,
# sem distinguir "esqueci de reverter" de "o dono mandou, eu mexi e documentei".
# Isso ja barrou uma alteracao legitima: o cooldown de margem, medido contra os
# 4.165 `EXEC_NO_MARGIN` do forward test.
#
# A CORRECAO NAO E afrouxar a guarda. E exigir que a autorizacao seja EXPLICITA
# e RASTREVEL: cada entrada deste arquivo declara o arquivo, o commit e o motivo,
# e a guarda so libera o que esta listado aqui.
#
# FORMATO: uma entrada por arquivo autorizado, mais o commit e o motivo.
# A guarda le isto; nao edite a guarda para passar.
#
# REGRA QUE PERMANECE: alterar `.mq5`/`.mqh` exige RECOMPILAR no MetaEditor64
# e REANEXAR ao grafico. A autorizacao para mexer no codigo NAO autoriza a
# reanexao automatica — ela derruba o treino de quem esta operando na DEMO.
# ===========================================================

AUTORIZACOES_MQL5: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------------
    # Limite de spread em porcentagem do preco (08/10/2026)
    # ---------------------------------------------------------------------
    "Core/Config.mqh": {
        "commit": "pendente",
        "motivo": (
            "MEDIDO na conta 391773676 com o EA operando BTCUSD H4: 4 de 12 "
            "simbolos bloqueados com spread NORMAL — BTCUSD (4000 pts), ETHUSD "
            "(300), USDSEK (1579) e o OURO (57 contra o limite de 50). O limite "
            "era em PONTOS CRUS e `point` varia mil vezes entre forex e BTCUSD: "
            "'50 pontos' vale $5,00 no BTCUSD (spread real $40) e $0,0005 no "
            "EURUSD (spread real $0,00019). Alem disso o mapa por simbolo nunca "
            "acertava: os nomes tinham `#` e `_Symbol` nao tem. Agora o limite e "
            "PORCENTAGEM do preco (0,6%) e o GetMaxSpread deriva os pontos do "
            "preco e do point do simbolo — os seis leitores nao mudaram."
        ),
        "compilado": "ver o log deste ciclo",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Enterprise/CircuitBreaker.mqh": {
        "commit": "pendente",
        "motivo": (
            "So o comentario que descrevia o defeito do limite de spread. "
            "Nenhuma logica mudou: a `emergencySpread = GetMaxSpread()*10` "
            "continua sendo a explosao extrema, agora sobre um numero ja "
            "convertido."
        ),
        "compilado": "ver o log deste ciclo",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Monitoring/ProductionChecklist.mqh": {
        "commit": "pendente",
        "motivo": (
            "Quarta instancia do mesmo defeito: comparava `spreadPoints` com o "
            "INPUT cru `MaxSpread`, e nao com `GetMaxSpread()`. O input virou "
            "porcentagem; quem converte para pontos e o getter. Sem isso o "
            "checklist dava o mesmo veredito para BTCUSD e EURUSD."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Monitoring/ValidationChecklist.mqh": {
        "commit": "pendente",
        "motivo": (
            "Mesma quarta instancia: `spreadPoints > MaxSpread` virou "
            "`spreadPoints > GetMaxSpread()`, e a mensagem mostra o limite "
            "convertido em vez do input cru."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "FASE_FINAL_20_5.SYMBOLS_AMPLIADO.set": {
        "commit": "pendente",
        "motivo": (
            "O preset carregava `MaxSpread=50` e "
            "`MaxSpreadBySymbol=GOLD#:350,BTCUSD#:600,ETHUSD#:600` — nomes que "
            "nao existem mais. Trocado por `MaxSpreadPct=0.6` e "
            "`MaxSpreadPctBySymbol=` (vazio: a medicao mostrou que o fallback "
            "de 0,6% ja da folga em todos os 12 simbolos). Sem trocar, o preset "
            "carregaria nomes inexistentes e o EA usaria o default."
        ),
        "compilado": "nao compila - e .set",
        "reanexado": "NAO - o dono escolhe qual preset carregar",
    },
    # ---------------------------------------------------------------------
    # Perda diaria = perda REALIZADA, e uma unica medida (08/10/2026)
    # ---------------------------------------------------------------------
    "Enterprise/SafetyManager.mqh": {
        "commit": "pendente",
        "motivo": (
            "MEDIDO na conta 391773676, conta REAL, com o AUTO ligado e uma "
            "posicao USDCAD aberta: `P/L: -0.16` e `[TRADE BLOCK] SAFETY | "
            "DD: 5.86%/5.00%`. O limite `MaxDailyLossPercent` diz LOSS; o codigo "
            "entregava DRAWDOWN pico-para-vale, e o pico (21,32) vinha de uma "
            "posicao recem-aberta com +6,90 de flutuante sobre saldo de 14,42. "
            "A ida e a volta de UMA posicao contava como perda diaria sem a "
            "conta ter perdido dinheiro. AGORA o numerador e o realizado do dia "
            "e o denominador e o SALDO do inicio do dia. Segunda correcao no "
            "mesmo dia: o gate ja usava a perda realizada mas `GetSafetySummary` "
            "ainda imprimia `GetDrawdownPercent()`, entao a tela dizia 5,02% e o "
            "operador procurava DD num bloqueio que era margem livre. Agora a "
            "formula mora em `GetDailyLossPercent()` e gate e tela consomem a "
            "mesma funcao, com o resumo nomeando as duas medidas: `PerdaDia` "
            "(a que trava) e `Amplitude` (pico-vale, informativa). "
            "`GetDrawdownPercent()` NAO foi mexido e continua servindo a "
            "RiskCenter, RiskEngine, Telemetry e CircuitBreaker."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": (
            "SIM do gate - verificado no journal em 08/10 21:29+, onde "
            "`[SAFETY] Daily DD limit` foi para 0 e `Daily loss limit` nunca "
            "disparou. NAO da tela: o resumo com `PerdaDia`/`Amplitude` "
            "depende do dono reanexar o EA no grafico."
        ),
    },
    "Enterprise/BackupManager.mqh": {
        "commit": "pendente",
        "motivo": (
            "MEDIDO 08/10/2026 22:14, conta REAL com o AUTO ligado: "
            "`[BACKUP] Backup com problemas | copiados=64 | falhas=44`, com 44 "
            "linhas `[BACKUP] Origem nao encontrada:` e o CAMINHO VAZIO depois "
            "dos dois pontos. `ExpandPattern` escrevia sempre a partir de "
            "`out[0]` e nao aceitava indice inicial, e o chamador a usava duas "
            "vezes no mesmo array — uma para FILE_COMMON e outra para LOCAL — "
            "somando os retornos em `found`. A segunda chamada sobrescrevia a "
            "primeira e `found` contava as duas: 44 do COMMON + 64 do LOCAL = "
            "108 posicoas percorridas com so 64 preenchidas; as 44 restantes "
            "eram lixo, com `origPath` vazio. Agora ha `start` como indice "
            "inicial e o retorno e a quantidade encontrada. Segunda correcao no "
            "mesmo lugar: entrada sem caminho e contada e dita no relatorio "
            "(`sem_caminho=`), em vez de virar copia de string vazia com erro "
            "sem caminho — que e o que mandava o operador procurar arquivo "
            "faltando em vez de indice faltando."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Release/v1.2.0/Config/XAU_AI_PRO.AUTOTRADE_ON.set": {
        "commit": "pendente",
        "motivo": (
            "MinFreeMargin 20.0 -> 10.0. MEDIDO na conta 391773676: o balance "
            "era 15,14 e a margem livre nunca passa do balance sem lucro "
            "flutuante, entao um piso de 20,00 nao era folga — era bloqueio "
            "permanente, e invertido: o EA so abria operacao quando a posicao "
            "aberta estava ganhando e bloqueava quando estava perdendo. "
            "Decisao do dono em 08/10/2026. Medido depois: 0,01 de GOLD custa "
            "4,15 de margem e deixa 14,71 livres, acima do novo piso de 10,00; "
            "com 20,00 nem 0,01 abria. Os tres presets (FASE_FINAL, AUTOTRADE_ON "
            "e ENDURANCE) e o default de `Core/Config.mqh` foram para 10.0, e os "
            "24 graficos com EA tambem, por `definir_input_ea`."
        ),
        "compilado": "nao compila - e .set",
        "reanexado": "SIM - 24 graficos gravados com backup, expertmode preservado",
    },
    "Release/v1.2.0-ENDURANCE/Config/XAU_AI_PRO.ENDURANCE.set": {
        "commit": "pendente",
        "motivo": (
            "Mesma mudanca e mesmo motivo de "
            "`Release/v1.2.0/Config/XAU_AI_PRO.AUTOTRADE_ON.set`: "
            "MinFreeMargin 20.0 -> 10.0, decisao do dono em 08/10/2026, porque "
            "um piso de 20,00 era inalcancavel num balance de 15,14."
        ),
        "compilado": "nao compila - e .set",
        "reanexado": "SIM - 24 graficos gravados com backup, expertmode preservado",
    },
    "Core/ExecutionEngine.mqh": {
        "commit": "pendente",
        "motivo": (
            "Risco por operacao em DINHEIRO em vez de pontos crus (decisao do "
            "dono, 08/10/2026). MEDIDO na conta 391773676: `StopLossPoints=300` "
            "valia US$ 3,00 no GOLD e US$ 3,00 no EURUSD, US$ 20 no USDJPY e "
            "US$ 0,03 no BTCUSD — um numero so, quatro riscos diferentes. E US$ "
            "3,00 contra um orcamento diario de 5% de US$ 12,13 = US$ 0,61: uma "
            "operacao estouraria o limite diario inteiro. Foi exatamente o que "
            "aconteceu: SELL 0,01 GOLD @ 4152,43 com stop em 4155,43 (+3,00) e "
            "alvo em 4146,43 (+6,00), tocado em ~1 minuto. Agora o risco vem de "
            "`RiskPerTradeUsd` e o alvo de `RiskPerTradeUsd * RewardRatio`, "
            "convertidos em pontos por `DistanciaPontosParaRiscoUSD`. "
            "MEDIDO apos a conversao: US$ 2,00 de stop e US$ 2,00 de alvo em "
            "GOLD, BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, USDCAD, USDCNH, "
            "USDSEK, AUDUSD, NZDUSD e USDCHF, e nenhum viola o stop level da "
            "corretora. Os inputs em PONTOS continuam como caminho de fuga "
            "quando `RiskPerTradeUsd <= 0`, entao nenhum controle fica sem "
            "consumidor."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Core/OrderManager.mqh": {
        "commit": "pendente",
        "motivo": (
            "Mesma correcao de `Core/ExecutionEngine.mqh`, na copia Buy e na "
            "copia Sell. Este arquivo estava com a formula de SL/TP DUPLICADA e "
            "divergindo do `ExecutionEngine`; agora os dois consomem a mesma "
            "funcao `DistanciaPontosParaRiscoUSD`. Registrado que "
            "`InitOrderManager()` nao tem chamador: o bloco e codigo morto "
            "hoje, e ficou corrigido justamente para nao ser a proxima "
            "divergencia quando alguem ligar."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - depende do dono reanexar o EA no grafico",
    },
    "Padrao_02_TP2_SL2.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 2, com `RiskPerTradeUsd=2` e `RewardRatio=1.0`, que da TP = SL = 2 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 200 pontos, EURUSD 200 pontos, USDCNH 200 pontos, USDJPY 20 pontos e BTCUSD 20000 pontos, todos valendo US$ 2,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_03_TP3_SL3.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 3, com `RiskPerTradeUsd=3` e `RewardRatio=1.0`, que da TP = SL = 3 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 300 pontos, EURUSD 300 pontos, USDCNH 300 pontos, USDJPY 30 pontos e BTCUSD 30000 pontos, todos valendo US$ 3,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_04_TP4_SL4.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 4, com `RiskPerTradeUsd=4` e `RewardRatio=1.0`, que da TP = SL = 4 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 400 pontos, EURUSD 400 pontos, USDCNH 400 pontos, USDJPY 40 pontos e BTCUSD 40000 pontos, todos valendo US$ 4,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_05_TP5_SL5.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 5, com `RiskPerTradeUsd=5` e `RewardRatio=1.0`, que da TP = SL = 5 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 500 pontos, EURUSD 500 pontos, USDCNH 500 pontos, USDJPY 50 pontos e BTCUSD 50000 pontos, todos valendo US$ 5,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_06_TP6_SL6.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 6, com `RiskPerTradeUsd=6` e `RewardRatio=1.0`, que da TP = SL = 6 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 600 pontos, EURUSD 600 pontos, USDCNH 600 pontos, USDJPY 60 pontos e BTCUSD 60000 pontos, todos valendo US$ 6,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_07_TP7_SL7.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 7, com `RiskPerTradeUsd=7` e `RewardRatio=1.0`, que da TP = SL = 7 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 700 pontos, EURUSD 700 pontos, USDCNH 700 pontos, USDJPY 70 pontos e BTCUSD 70000 pontos, todos valendo US$ 7,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_08_TP8_SL8.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 8, com `RiskPerTradeUsd=8` e `RewardRatio=1.0`, que da TP = SL = 8 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 800 pontos, EURUSD 800 pontos, USDCNH 800 pontos, USDJPY 80 pontos e BTCUSD 80000 pontos, todos valendo US$ 8,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_09_TP9_SL9.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 9, com `RiskPerTradeUsd=9` e `RewardRatio=1.0`, que da TP = SL = 9 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 900 pontos, EURUSD 900 pontos, USDCNH 900 pontos, USDJPY 90 pontos e BTCUSD 90000 pontos, todos valendo US$ 9,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Padrao_10_TP10_SL10.set": {
        "commit": "pendente",
        "motivo": (
                "Escada de setups padrao pedida pelo dono em 08/10/2026: montar meu setup ordens padrao, alvo 2 USD de TP com 2 USD de SL, padrao 2 com 3, padrao 3 com 4. Ou seja, TP = SL = N dolares. Este e o padrao 10, com `RiskPerTradeUsd=10` e `RewardRatio=1.0`, que da TP = SL = 10 USD em qualquer simbolo pela conversao `DistanciaPontosParaRiscoUSD`. MEDIDO com 0,01 de lote: GOLD 1000 pontos, EURUSD 1000 pontos, USDCNH 1000 pontos, USDJPY 100 pontos e BTCUSD 100000 pontos, todos valendo US$ 10,00. O molde NAO foi o preset FASE_FINAL porque aquele ainda traz `MaxSpread` e `MaxSpreadBySymbol`, que nao existem mais, e inclui `XAUUSD`, simbolo que a XMGlobal nao oferece nesta conta. O ouro dela e `GOLD`."
            ),
            "compilado": "nao compila - e .set",
            "reanexado": "NAO - o dono escolhe qual padrao carregar",
    },
    "Core/RiskHub.mqh": {
        "commit": "pendente",
        "motivo": (
            "Trabalho que existia so na arvore principal do terminal e de que o "
            "repo precisa para compilar a correcao acima: `GetEffectiveDaily"
            "TradesCount()` e `GetDailyHistoryTradesCount()`, que contam as "
            "entradas EFETIVAMENTE executadas no historico do dia (filtrando por "
            "magic e por DEAL_ENTRY_IN/INOUT) em vez de so o contador "
            "persistente. O contador persistente continua sendo usado para cobrir "
            "as ordens novas antes de o historico ficar disponivel. Portado do "
            "terminal: a diferenca para o repo era de 43 linhas e ZERO linhas "
            "exclusivas do repo, ou seja, nao ha trabalho local a perder."
        ),
        "compilado": "0 errors, 0 warnings",
        "reanexado": "NAO - a arvore principal ja roda esta versao",
    },
    # ---------------------------------------------------------------------
    # Cooldown de margem
    # ---------------------------------------------------------------------
    "Enterprise/MarginChecker.mqh": {
        "commit": "pendente",
        "motivo": (
            "EXEC_NO_MARGIN repetido a cada 2-3 s: 4.165 recusas no forward test, "
            "1.452 num unico dia (17/09). A trava de margem EXISTIA e funcionava; o "
            "defeito era insistir depois de recusado. Cooldown por simbolo com backoff "
            "60 s -> 1 h. Reducao medida de 3.191x nas recusas."
        ),
        "compilado": "sim — MetaEditor64, 0 errors, 0 warnings, XAU_AI_PRO.ex5 419.654 bytes",
        "reanexado": "NAO — attente o treino do dono na conta DEMO",
    },
    "Core/ExecutionEngine.mqh": {
        "commit": "pendente",
        "motivo": (
            "OrderSendResult() NAO existe em MQL5 (error 256), introduzido no commit "
            "dbdce10 e nunca compilado. Nao havia .ex5 versionado para revelar isso. "
            "Substituido por GetLastError() com traducao explicita do ExecResult, para "
            "que o BROKER_ERROR passe a dizer a CAUSA."
        ),
        "compilado": "sim — junto com o acima, 0 errors, 0 warnings",
        "reanexado": "NAO — mesma razao",
    },
    # ---------------------------------------------------------------------
    # Modulos que existem SO no terminal do MT5
    # ---------------------------------------------------------------------
    "XAU_AI_PRO_ORFAOS_DO_TERMINAL/SignalCoreV2.mqh": {
        "commit": "pendente",
        "motivo": (
            "COPIA VERBATIM, NAO ALTERACAO. "
            "terminal e NUNCA versionados em nenhuma branch (verificado com "
            "git log --all --diff-filter=A). Modulo de estrategia paralelo "
            "('Signal Core v2 - hipotese: breakout de tendencia'), com seletor "
            "SignalCoreVersion e SignalCoreV2Init()/Release() chamados pelo "
            "XAU_AI_PRO.mq5 do terminal. Copiar o repo por cima do terminal "
            "APAGARIA este trabalho. Copiado verbatim, sem alteracao."
        ),
        "compilado": "nao — sera compilado junto com a reintegracao",
        "reanexado": "NAO",
    },
    "XAU_AI_PRO_ORFAOS_DO_TERMINAL/EAHeartbeat.mqh": {
        "commit": "pendente",
        "motivo": (
            "COPIA VERBATIM, NAO ALTERACAO. "
            "NUNCA versionado. Ponte somente leitura EA -> Gateway -> "
            "App: grava XAU_AI_PRO_heartbeat.json (FILE_COMMON), consumido por "
            "backend/ea_manager.py:186. O arquivo em disco confirma "
            "server=MetaQuotes-Demo. Copiado verbatim, sem alteracao."
        ),
        "compilado": "nao — sera compilado junto com a reintegracao",
        "reanexado": "NAO",
    },
    "XAU_AI_PRO_ORFAOS_DO_TERMINAL/XAU_AI_PRO.mq5": {
        "commit": "pendente",
        "motivo": (
            "COPIA VERBATIM, NAO ALTERACAO. "
            "O repo tem 53.646 e o terminal 59.802: sao versoes DIVERGENTES do mesmo EA, e a do terminal e a "
            "que o MT5 carrega. Esta e a copia que inclui SignalCoreV2 e "
            "EAHeartbeat. Fica versionada para que a divergencia entre as duas "
            "copias seja um diff, e nao um mistério."
        ),
        "compilado": "nao",
        "reanexado": "NAO",
    },
    "Core/SignalCoreV2.mqh": {
        "commit": "pendente",
        "motivo": (
            "Integracao do modulo de estrategia paralelo que existia apenas no "
            "terminal do MT5. Copiado verbatim do original (que esta em "
            "XAU_AI_PRO_ORFAOS_DO_TERMINAL/) e ligado ao .mq5 em 4 pontos: "
            "include, SignalCoreV2Init(), SignalCoreV2Release() e o heartbeat. "
            "Sem isto o repo nao reproduz o EA que o MT5 executa."
        ),
        "compilado": "sim - MetaEditor64, 0 errors, 0 warnings",
        "reanexado": "NAO - attente o treino na conta DEMO",
    },
    "Integration/EAHeartbeat.mqh": {
        "commit": "pendente",
        "motivo": (
            "Integracao do modulo de heartbeat que existia apenas no terminal. "
            "Grava XAU_AI_PRO_heartbeat.json (FILE_COMMON), consumido por "
            "backend/ea_manager.py para dizer se o EA esta vivo. Copiado "
            "verbatim, sem alteracao."
        ),
        "compilado": "sim - junto com o acima",
        "reanexado": "NAO - mesma razao",
    },
    "Enterprise/VersionManager.mqh": {
        "commit": "pendente",
        "motivo": (
            "EA_VERSION_STRING estava em 1.2.0 com o produto em 1.2.4: o "
            "`[VERSION]` que o EA escreve no log, e que a tela mostra, "
            "divulgava uma versao que nao existe mais. Este modulo nao esta "
            "na lista do sync_version.py, entao `--check` nao via a divergencia."
        ),
        "compilado": "sim - junto com o acima",
        "reanexado": "NAO - mesma razao",
    },
    "Enterprise/BackupManager.mqh": {
        "commit": "pendente",
        "motivo": (
            "O manifesto do backup gravava a versao do EA como literal solto "
            "(\"v1.2.0\"), em um ARQUIVO lido so na restauracao: divergia ha "
            "quatro versoes sem ninguem ver. Passa a usar EA_VERSION_STRING. "
            "Exige o include de VersionManager.mqh porque o .mq5 inclui este "
            "arquivo antes daquele."
        ),
        "compilado": "sim - junto com o acima",
        "reanexado": "NAO - mesma razao",
    },
    "XAU_AI_PRO.mq5": {
        "commit": "pendente",
        "motivo": (
            "Duas correcoes. (1) `#property version` dizia \"1.20\" com o "
            "produto em 1.2.4, e o MT5 mostra esse valor na aba de "
            "propriedades do EA. (2) Ligacao do SignalCoreV2 e do heartbeat "
            "nos mesmos pontos em que o terminal os usa."
        ),
        "compilado": "sim - junto com o acima",
        "reanexado": "NAO - mesma razao",
    },
    "Core/Config.mqh": {
        "commit": "pendente",
        "motivo": (
            "AIRequestTimeoutMs 5000 -> 15000: medido em 05/10/2026, o "
            "primeiro acesso ao par leva 2096 ms (carrega o `.pkl` em disco "
            "frio) e timeout curto faria o EA cair sem sinal na consulta que "
            "mais importa. So comentario + 1 input, sem logica."
        ),
        "compilado": "sim - MetaEditor64 via tests/test_mql5_compila.py, 0 errors",
        "reanexado": "NAO - mesma razao",
    },
    "Enterprise/CircuitBreaker.mqh": {
        "commit": "pendente",
        "motivo": (
            "So a FREQUENCIA do log de diagnostico. MEDIDO em 07/10/2026 na "
            "conta 391773676: 934.078 linhas / 139,2 MB de journal em um dia, "
            "com 57.393 linhas de [CIRCUIT] SPREAD EXPLOSION e outras 57.393 de "
            "[CIRCUIT] SPREAD ALTO no mesmo tique. `CheckSpreadExplosion` "
            "continua devolvendo true nos mesmos tiques com o mesmo limite e "
            "`RunSymbol` continua delegando o bloqueio ao ValidateTrade - o "
            "proprio comentario da linha 879 dizia que esse log 'serve apenas "
            "de diagnostico'. Throttle de 60 s por simbolo."
        ),
        "compilado": "PENDENTE - medir apos compilar",
        "reanexado": "NAO - o dono reanexa (AGENTS.md §7)",
    },
}


def _autorizacoes_mql5() -> dict[str, dict[str, str]]:
    """Mapa `arquivo relativo` -> `{commit, motivo, compilado, reanexado}`."""
    return AUTORIZACOES_MQL5


# Espaco minimo livre para as operacoes longas do projeto.
DISCO_MINIMO_GB = 4.0
# Espaco minimo para build Android (Gradle + target Rust).
DISCO_MINIMO_ANDROID_GB = 8.0

# Portas do produto. Todas precisam estar livres antes de subir o app.
PORTAS = {"gateway": 9001, "websocket": 9002, "core": 9003}

PORTA_GATEWAY_PADRAO = 9001


def porta_do_gateway() -> int:
    """A porta em que o gateway DESTE ambiente escuta.

    MEDIDO em 10/10/2026: com `XAU_GATEWAY_PORT=9011` no ambiente do usuario, o
    app subiu o gateway em 9011 e o preflight mediu 9001 — que estava livre
    justamente porque o processo escutava em outra porta — e deu `ok`. Duas
    verdades do mesmo dado divergindo, que e a regra 5 do AGENTS.md: quem
    media inventava um numero, e a resposta nao acusava nada.

    A variavel de ambiente e a fonte. O frontend ja tinha aprendido isso em
    `frontend/src/lib/portas.ts` (09/10/2026): o mesmo nome, lido pelo Tauri no
    boot. O preflight ficou de fora e media a porta que ele mesmo escreveu.
    """
    bruta = (os.environ.get("XAU_GATEWAY_PORT") or "").strip()
    try:
        porta = int(bruta)
    except ValueError:
        return PORTA_GATEWAY_PADRAO
    if 1024 <= porta <= 65535:
        return porta
    return PORTA_GATEWAY_PADRAO

# Ferramentas obrigatorias por etapa. No Windows, `npm` e um .cmd e precisa ser
# chamado pelo nome completo; `python` raramente esta no PATH porque o projeto
# usa sempre .venv\Scripts\python.exe (ver checar_python_do_projeto).
FERRAMENTAS = {
    "node": ("node", "--version"),
    "npm": ("npm.cmd" if os.name == "nt" else "npm", "--version"),
    "cargo": ("cargo", "--version"),
}

# Scripts removidos em 2026-09-26. Ver scripts/validate_release.ps1.
SCRIPTS_BLOQUEADOS = (
    "cmd.exe",
    "XAU_AI_PRO_START.vbs",
    "scripts/overnight_session.ps1",
    "scripts/ciclo_limpo_123.py",
    "Tools/pos_reboot_docker.ps1",
    "Tools/post_docker_cli_setup.ps1",
    "Tools/connect_sandbox_claude.ps1",
    "Tools/setup_sandbox_claude.ps1",
    "Tools/vercel_vcr_setup.ps1",
    "Tools/install_docker.bat",
    "Tools/install_docker_windows.ps1",
    "setup-vercel.bat",
)

# Flags de execucao: o app nasce desbloqueado (padrao de codigo = aberto).
# Aqui so se reporta o que foi ligado/desligado EXPLICITAMENTE na variavel de
# ambiente, porque e a unica coisa que o console declara contra o padrao.
FLAGS_DE_EXECUCAO = (
    "XAU_ENABLE_REAL_ORDERS",
    "XAU_MCP_TRADING",
    "XAU_ENABLE_EMERGENCY_RESUME",
)

# Flags de paper/demo: legais no dia a dia, apenas informative.
FLAGS_DE_DEMO = ("XAU_ENABLE_TRADE_COMMANDS",)

ESTADOS = {"ok": "OK", "aviso": "AVISO", "falha": "FALHA", "pulado": "pulado"}


@dataclass
class Resultado:
    nome: str
    estado: str
    detalhe: str = ""
    dica: str = ""


@dataclass
class Relatorio:
    resultados: list[Resultado] = field(default_factory=list)

    def add(self, resultado: "Resultado") -> None:
        self.resultados.append(resultado)

    @property
    def falhas(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == ESTADOS["falha"]]

    @property
    def avisos(self) -> list[Resultado]:
        return [r for r in self.resultados if r.estado == ESTADOS["aviso"]]

    def ok_para_operacao_longa(self) -> bool:
        return not self.falhas


# --------------------------------------------------------------------- disco


def checar_disco(minimo_gb: float = DISCO_MINIMO_GB) -> Resultado:
    livre = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if livre < minimo_gb:
        return Resultado(
            "disco livre",
            ESTADOS["falha"],
            f"{livre:.2f} GB (minimo {minimo_gb:.1f} GB)",
            "python scripts/limpeza_segura.ps1 -BuildArtifacts -DebugCache -Apply",
        )
    if livre < minimo_gb * 2:
        return Resultado(
            "disco livre", ESTADOS["aviso"], f"{livre:.2f} GB",
            "opere com cuidado: build Android exige mais espaco",
        )
    return Resultado("disco livre", ESTADOS["ok"], f"{livre:.2f} GB")


# ---------------------------------------------------------------- ferramentas


def checar_ferramentas() -> list[Resultado]:
    resultados = []
    for nome, comando in FERRAMENTAS.items():
        executavel = shutil.which(comando[0])
        if not executavel:
            resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["falha"], "nao encontrada no PATH"))
            continue
        try:
            saida = subprocess.run(
                list(comando), capture_output=True, text=True, timeout=25, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["aviso"], f"erro ao consultar: {exc}"))
            continue
        resultados.append(Resultado(f"ferramenta {nome}", ESTADOS["ok"], saida or executavel))
    return resultados


def checar_python_do_projeto() -> Resultado:
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        return Resultado(
            "python do projeto", ESTADOS["falha"], ".venv/Scripts/python.exe ausente",
            "python -m venv .venv e instale requirements.txt + requirements-dev.txt",
        )
    return Resultado("python do projeto", ESTADOS["ok"], str(python.relative_to(ROOT)))


# ---------------------------------------------------------------------- rede


def porta_livre(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", porta)) != 0


def checar_portas(esperar_livre: bool) -> list[Resultado]:
    resultados = []
    portas = {**PORTAS, "gateway": porta_do_gateway()}
    for nome, porta in portas.items():
        livre = porta_livre(porta)
        if esperar_livre:
            if livre:
                resultados.append(Resultado(f"porta {porta} ({nome})", ESTADOS["ok"], "livre"))
            else:
                resultados.append(
                    Resultado(f"porta {porta} ({nome})", ESTADOS["falha"], "ocupada",
                          "feche o app instalado ou o processo que segura a porta antes de subir outro")
                )
        elif livre:
            resultados.append(
                Resultado(f"porta {porta} ({nome})", ESTADOS["falha"], "livre",
                      "a etapa app-rodando exige o processo escutando aqui: "
                      "suba o app pelo atalho, ou confira XAU_GATEWAY_PORT se o gateway usa outra porta")
            )
        else:
            resultados.append(
                Resultado(f"porta {porta} ({nome})", ESTADOS["ok"], "ocupada (app em execucao)")
            )
    return resultados


# ------------------------------------------------------------------ git/mql5


def _git(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=40, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return proc.returncode, (proc.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def checar_mql5() -> Resultado:
    """MQL5/Experts e intocavel sem autorizacao DECLARADA.

    Qualquer alteracao e bloqueio imediato, SALVO os arquivos listados em
    `AUTORIZACOES_MQL5` — que existe para exigir que a mudanca seja
    rastreavel (autorizacao + commit + motivo), e nao para afrouxar a guarda.

    Antes a guarda reprovava qualquer diff. Isso travou uma
    alteracao legitima e medida (cooldown de margem), mas o modo de falha
    oposto e pior: uma guarda que aceita tudo depois de ser "contornada" uma
    vez deixa de valer. Aqui ela continua reprovando o que nao esta declarado.

    Detalhe que importa: o caminho e RELATIVO a `MQL5/Experts`, porque e assim
    que `git status --porcelain -- MQL5/Experts` devolve.
    """
    status, saida = _git("status", "--porcelain", "--", "MQL5/Experts")
    if status != 0:
        return Resultado("guarda MQL5", ESTADOS["aviso"], "nao foi possivel consultar o git")
    if not saida:
        return Resultado("guarda MQL5", ESTADOS["ok"], "MQL5/Experts intacto")

    autorizado = _autorizacoes_mql5()
    nao_declarados: list[str] = []
    declarados: list[str] = []
    for linha in saida.splitlines():
        # Formato do porcelain: "<XY> <caminho>", com XY ocupando 2
        # caracteres e UM espaco de separacao — `linha[3:]` funciona, mas
        # `split(maxsplit=1)` e o que sobrevive a um "\t" no lugar do espaco,
        # que e o mesmo bug de encoding que ja mordeu o dataset e o CSV do
        # forward test.
        partes = linha.split(None, 1)
        if len(partes) != 2:
            # Linha sem caminho (raro, mas nao vale derrubar o preflight).
            nao_declarados.append(linha.strip())
            continue
        caminho = partes[1].strip().strip('"')
        # Normaliza para relativo a MQL5/Experts, como esta no dicionario.
        relativo = caminho
        for prefixo in ("MQL5/Experts/XAU_AI_PRO/", "MQL5/Experts/"):
            if relativo.startswith(prefixo):
                relativo = relativo[len(prefixo):]
                break
        (declarados if relativo in autorizado else nao_declarados).append(caminho)

    if nao_declarados:
        return Resultado(
            "guarda MQL5",
            ESTADOS["falha"],
            f"{len(nao_declarados)} arquivo(s) sem autorizacao: {', '.join(sorted(nao_declarados))}",
            "MQL5 e intocavel: reverta com git checkout -- MQL5/Experts, ou declare a "
            "alteracao em AUTORIZACOES_MQL5 (scripts/preflight.py) com commit e motivo",
        )

    return Resultado(
        "guarda MQL5",
        ESTADOS["aviso"],
        f"{len(declarados)} arquivo(s) com autorizacao declarada: {', '.join(sorted(declarados))}",
        "alteracao MQL5 autorizada: confirme que COMPILOU no MetaEditor64 e "
        "REANEXOU ao grafico antes de tratar como valida",
    )


def checar_git() -> list[Resultado]:
    resultados = []
    status, saida = _git("diff", "--check")
    if status == 0:
        resultados.append(Resultado("git diff --check", ESTADOS["ok"], "sem erro de whitespace"))
    else:
        resultados.append(Resultado("git diff --check", ESTADOS["falha"], saida[:200] or "erro"))
    _, pendentes = _git("status", "--porcelain")
    quantidade = len([linha for linha in pendentes.splitlines() if linha.strip()])
    estado = ESTADOS["aviso"] if quantidade else ESTADOS["ok"]
    resultados.append(Resultado("arquivos pendentes no git", estado, str(quantidade)))
    return resultados


# ------------------------------------------------------------------- limpeza


def checar_scripts_bloqueados() -> Resultado:
    presentes = [rel for rel in SCRIPTS_BLOQUEADOS if (ROOT / rel).exists()]
    if presentes:
        return Resultado(
            "scripts perigosos", ESTADOS["falha"], ", ".join(presentes),
            "esses scripts fazem autoexecucao, limpeza automatica ou baixam binarios em silencio",
        )
    return Resultado("scripts perigosos", ESTADOS["ok"], "nenhum presente")


def checar_binarios_na_raiz() -> Resultado:
    extensoes = {".exe", ".dll", ".vbs", ".scr", ".sys"}
    achados = [p.name for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in extensoes]
    if achados:
        return Resultado(
            "binarios na raiz", ESTADOS["falha"], ", ".join(sorted(achados)),
            "binario solto sombreia o do sistema (ja aconteceu com cmd.exe) e atrai heuristica de AV",
        )
    return Resultado("binarios na raiz", ESTADOS["ok"], "nenhum")


def checar_flags_de_execucao() -> Resultado:
    ligadas = [f for f in FLAGS_DE_EXECUCAO if os.getenv(f) == "1"]
    if ligadas:
        return Resultado(
            "flags de execucao", ESTADOS["falha"], f"explicitas: {', '.join(ligadas)}",
            "o padrao do codigo e aberto; declare a flag so quando quiser divergir do padrao",
        )
    demos = [f for f in FLAGS_DE_DEMO if os.getenv(f) == "1"]
    detalhe = "nenhuma flag explicita (padrao de codigo aberto)"
    if demos:
        detalhe = f"padrao aberto; paper/demo declarado: {', '.join(demos)}"
    return Resultado("flags de execucao", ESTADOS["ok"], detalhe)


def checar_versao() -> Resultado:
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.sync_version import TARGETS, current_version, load_version

        esperado = load_version()
        divergentes = [label for label, path in TARGETS if path.exists() and current_version(path) != esperado]
        if divergentes:
            return Resultado(
                "versao do projeto", ESTADOS["aviso"],
                f"divergente em {len(divergentes)}: {', '.join(divergentes)}",
                "python scripts/sync_version.py",
            )
        return Resultado("versao do projeto", ESTADOS["ok"], esperado)
    except Exception as exc:  # noqa: BLE001 - o preflight nao pode cair
        return Resultado("versao do projeto", ESTADOS["aviso"], f"nao verificada: {exc}")


# ------------------------------------------------------------------- entrada


def executar(etapa: str = "longa") -> Relatorio:
    """Monta o relatorio. `etapa` ajusta o que e bloqueante."""
    relatorio = Relatorio()

    def add(resultado: Resultado) -> None:
        relatorio.resultados.append(resultado)

    minimo = DISCO_MINIMO_ANDROID_GB if etapa == "android" else DISCO_MINIMO_GB
    add(checar_disco(minimo))
    for resultado in checar_ferramentas():
        add(resultado)
    add(checar_python_do_projeto())
    for resultado in checar_portas(esperar_livre=etapa != "app-rodando"):
        add(resultado)
    add(checar_mql5())
    for resultado in checar_git():
        add(resultado)
    add(checar_scripts_bloqueados())
    add(checar_binarios_na_raiz())
    add(checar_flags_de_execucao())
    add(checar_versao())
    return relatorio


def imprimir(relatorio: Relatorio) -> None:
    largura = max((len(r.nome) for r in relatorio.resultados), default=10)
    for r in relatorio.resultados:
        marca = {"OK": "[ ok ]", "AVISO": "[ !! ]", "FALHA": "[XX  ]", "pulado": "[ -- ]"}[r.estado]
        print(f"{marca} {r.nome.ljust(largura)}  {r.detalhe}")
        if r.dica and r.estado in {ESTADOS["falha"], ESTADOS["aviso"]}:
            print(f"        -> {r.dica}")
    print()
    if relatorio.falhas:
        print(f"BLOQUEADO: {len(relatorio.falhas)} falha(s). Corrija antes de comecar a operacao.")
    elif relatorio.avisos:
        print(f"Atencao: {len(relatorio.avisos)} aviso(s), nenhuma falha bloqueante.")
    else:
        print("Tudo pronto para a operacao.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificacao de ambiente do XAU AI PRO (somente leitura)")
    parser.add_argument("--etapa", default="longa", choices=["longa", "android", "app-rodando"],
                        help="ajusta o que e bloqueante: disco minimo e exigencia de portas livres")
    parser.add_argument("--json", action="store_true", help="saida em JSON")
    args = parser.parse_args()

    relatorio = executar(args.etapa)
    if args.json:
        print(json.dumps({
            "ok": relatorio.ok_para_operacao_longa(),
            "itens": [
                {"nome": r.nome, "estado": r.estado, "detalhe": r.detalhe, "dica": r.dica}
                for r in relatorio.resultados
            ],
        }, ensure_ascii=False, indent=2))
    else:
        imprimir(relatorio)
    return 0 if relatorio.ok_para_operacao_longa() else 1


if __name__ == "__main__":
    sys.exit(main())
