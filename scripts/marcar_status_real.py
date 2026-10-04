"""Acrescenta um aviso destatus real nos documentos que afirmam prontidao sem lastro.

Cada item foi conferido em disco ou no codigo antes de entrar aqui:

1. INTEGRACAO_SENTRY_COMPLETA.md:170 - "TUDO PRONTO PARA PRODUCAO!" sem gate nem
   evidencia. Contraria LAUDO_FINAL_AUDITORIA.md:18 e
   ACOMPANHAMENTO_OFICIAL_PC_20260921.md:430 ("nao aprovado ainda").
   > ATUALIZADO 04/10/2026: o arquivo foi REMOVIDO do repositorio junto com o
   > Sentry. O aviso abaixo continua no dicionario porque o script e
   > idempotente e simplesmente pula quem nao existe (ver `main()`).
2. RESUMO_INTEGRACAO.md:207 - "Sistema pronto para producao!".
3. LAUDO_FINAL_AUDITORIA.md:117 - "APROVADA (10/10)" na camada de execucao
   financeira, no mesmo documento que diz (linha 18) que dinheiro real nao esta
   liberado. A propria DECISOES_PRODUTO_20260925.md:35 proibe nota "10/10" sem
   evidencia.
4. ROADMAP_MOBILE.md:20 - "Rate limiting: Pronto". O codigo existe
   (mt5_gateway.py:81-82), mas o default e 0 = ilimitado, e o MCP nao tem
   rate limit algum (backend/trading_mcp.py).
5. Docs/contracts/ea_python_app_contract.md:702 - "esta pronto como". A IA esta
   inerte (prediction.json com 67 dias e symbol errado), o endurance nunca rodou
   e o log do MT5 chegou a 1,7 GB.

O aviso e aplicado uma unica vez: o script detecta o marcador e nao duplica.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARCADOR = "<!-- status-real-2026-09-27 -->"

AVISOS = {
    "INTEGRACAO_SENTRY_COMPLETA.md": (
        "## Status real (2026-09-27)\n\n"
        "A frase \"TUDO PRONTO PARA PRODUCAO!\" nao se sustenta. O produto esta em\n"
        "`PRODUCTION CANDIDATE` e nao foi promovido:\n\n"
        "- Endurance 24h/72h/7d **nunca executada** (CP1-CP5 vazios em\n"
        "  `ENDURANCE_20_6_PROTOCOLO.md:44-48`).\n"
        "- Forward test em conta DEMO **nada executado**.\n"
        "- Profit Factor medido **0,46** com 57% de acerto: reprovado\n"
        "  economicamente (`Docs/production_gate_etapa24.md:57`).\n"
        "- **8 condicoes de seguranca para dinheiro real, todas abertas**\n"
        "  (`RELATORIO_AUDITORIA_SEGURANCA.md:187-199`).\n"
        "- Assinatura dos binarios e **autoassinada de teste**; sem certificado\n"
        "  publico, a reputacao no SmartScreen e zero.\n"
        "- `release/1.2.3/release-manifest.json` com os hashes **nao existe**.\n\n"
        "Ver tambem `LAUDO_FINAL_AUDITORIA.md:18` e\n"
        "`ACOMPANHAMENTO_OFICIAL_PC_20260921.md:430`.\n"
    ),
    "RESUMO_INTEGRACAO.md": (
        "## Status real (2026-09-27)\n\n"
        "\"Sistema pronto para producao\" nao se sustenta. Ver\n"
        "`INTEGRACAO_SENTRY_COMPLETA.md` e `CONVERSAHOJE.txt` para o inventario\n"
        "completo. Resumo: `PRODUCTION CANDIDATE`; endurance e forward test nunca\n"
        "rodaram; PF 0,46; 8 condicoes de seguranca abertas; assinatura de teste.\n"
    ),
    "LAUDO_FINAL_AUDITORIA.md": (
        "## Correcao de status (2026-09-27)\n\n"
        "A linha 117 dava **APROVADA (10/10)** a camada de execucao financeira, no\n"
        "mesmo documento que afirma (linha 18) que dinheiro real nao esta liberado.\n"
        "A nota foi rebaixada para **aprovada com ressalvas**.\n\n"
        "Ressalvas concretas, verificadas no codigo:\n\n"
        "- `_real_order` recusa incondicionalmente (`backend/mt5_gateway.py:1697`):\n"
        "  nao existe caminho de ordem real implementado.\n"
        "- Nenhum adaptador de execucao e importado por `mt5_gateway.py` nem por\n"
        "  `fastapi_gateway.py`; os cinco arquivos `*_execution.py` estao orfaos.\n"
        "- Abertura de posicao DEMO nao gravava `intent_log` (corrigido em\n"
        "  2026-09-27) e o `audit_log` nao era chamado no processo empacotado.\n"
        "- `risk_gate.py` tinha `max_spread`/`max_notional` como `None`, o que\n"
        "  desligava as duas travas; agora sao obrigatorios e falha fechada.\n\n"
        "A proibicao de prometer \"10/10\" sem evidencia esta em\n"
        "`Docs/DECISOES_PRODUTO_20260925.md:35`.\n"
    ),
    "ROADMAP_MOBILE.md": (
        "## Correcao de status (2026-09-27)\n\n"
        "A linha 20 marcava Rate limiting como \"Pronto\". O codigo existe\n"
        "(`backend/mt5_gateway.py:81-82`, `backend/server-desktop.cjs:183`), mas:\n\n"
        "- o default e **0 = ilimitado** (comentario na propria linha 81);\n"
        "- o Tauri **nao define** `XAU_RATE_LIMIT` ao subir o gateway\n"
        "  (`frontend/src-tauri/src/main.rs:387-393`), entao segue desligado;\n"
        "- `backend/trading_mcp.py` **nao tem** nenhum rate limit.\n\n"
        "Status correto: **existe, porem desligado por padrao**.\n"
    ),
    "Docs/contracts/ea_python_app_contract.md": (
        "## Correcao de status (2026-09-27)\n\n"
        "A linha 702 afirma que o conjunto \"esta pronto como\" produto. O que foi\n"
        "verificado no estado real:\n\n"
        "- **A IA esta inerte**: `MQL5/Files/Data/prediction.json` tem\n"
        "  `symbol: BTCUSDC`, `timestamp` de 67 dias e `model_version 1.1.0`, para\n"
        "  um EA configurado em XAUUSD. `system_status.json` reporta\n"
        "  `ai.available: false, stale: true`. O fail-safe funciona (nao vira sinal\n"
        "  errado), mas **todas as decisoes vem do fallback heuristico local**.\n"
        "- Falta `XAUUSD_M15.pkl`, que e o timeframe de backtest do produto\n"
        "  (`Python/models/` tem H1, H4 e M5).\n"
        "- Endurance nunca executada; forward test nunca executado.\n"
        "- `MQL5/Logs` chegou a 1,7 GB em 6 dias: `ValidationEngine.mqh` imprime\n"
        "  em todo tick aprovado, sem throttle.\n\n"
        "Ver `CONVERSAHOJE.txt` para o inventario atualizado.\n"
    ),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    aplicados = 0
    for nome, aviso in AVISOS.items():
        caminho = Path(nome)
        if not caminho.exists():
            print(f"SKIP {nome}: ausente")
            continue
        texto = caminho.read_text(encoding="utf-8", errors="replace")
        if MARCADOR in texto:
            print(f"JA   {nome}")
            continue
        caminho.write_text(texto.rstrip() + "\n\n" + MARCADOR + "\n\n" + aviso, encoding="utf-8")
        print(f"OK   {nome}")
        aplicados += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
