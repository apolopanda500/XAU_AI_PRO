# -*- coding: utf-8 -*-
"""Guarda automatizada de neutralidade: zero ativo fixo e zero marcas externas."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERMOS_PROIBIDOS = ["FTMO", "FUNDEDNEXT", "THE5ERS", "TRADINGVIEW", "OANDA:", "MEXC", "BINANCE"]
ARQUIVOS_AUDITADOS = [
    "frontend/src/components/AssetSymbolPicker.tsx",
    "frontend/src/components/OrderTicketPro.tsx",
    "frontend/src/components/InstitutionalDesk.tsx",
    "frontend/src/components/BankrollAndOrdersPanel.tsx",
    "frontend/src/components/FirstRunWizard.tsx",
    "frontend/src/components/ModelCards3DGrid.tsx",
    "frontend/src/components/LiveAiRiskCopilot.tsx",
    "frontend/src/hooks/useAlwaysLiveChart.ts",
    "backend/models_profiles_api.py",
    "Python/train_universal_onnx.py",
]


def test_zero_marcas_externas_nos_componentes_novos():
    violacoes = []
    for rel in ARQUIVOS_AUDITADOS:
        alvo = ROOT / rel
        if not alvo.exists():
            continue
        c = alvo.read_text(encoding="utf-8", errors="ignore").upper()
        for termo in TERMOS_PROIBIDOS:
            if termo in c:
                violacoes.append(f"{rel}: marca externa '{termo}'")
    assert not violacoes, f"Violação de neutralidade: {violacoes}"


def test_zero_simbolo_fixo_no_codigo_dos_componentes_novos():
    import io, tokenize, re
    simbolos = ("XAUUSD", "EURUSD", "BTCUSD", "GBPUSD", "USDJPY")
    violacoes = []
    for rel in ARQUIVOS_AUDITADOS:
        alvo = ROOT / rel
        if not alvo.exists() or alvo.suffix not in (".ts", ".tsx", ".py"):
            continue
        fonte = alvo.read_text(encoding="utf-8", errors="ignore")
        codigo = []
        if alvo.suffix == ".py":
            try:
                for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
                    if tok.type not in (tokenize.STRING, tokenize.COMMENT):
                        codigo.append(tok.string.upper())
            except (tokenize.TokenError, IndentationError):
                codigo = [fonte.upper()]
        else:
            sem = re.sub(r"//.*|/\*[\s\S]*?\*/", " ", fonte)
            codigo = [re.sub(r"['\"`][^'\"`]*['\"`]", " ", sem).upper()]
        txt = " ".join(codigo)
        for simbolo in simbolos:
            if simbolo in txt:
                violacoes.append(f"{rel}: símbolo presumido '{simbolo}'")
    assert not violacoes, f"Violação de agnosticismo: {violacoes}"
