"""
XAU AI PRO - API Backend (FastAPI)
Endpoints:
  GET  /                          -> status
  GET  /prediction/{symbol}       -> predição de um símbolo
  GET  /account                   -> dados da conta (SQLite)
  GET  /market/live               -> cotações em tempo real (MT5/yfinance)
  GET  /market/live/{symbol}      -> cotação de um símbolo
  GET  /predictions               -> lista todas as predições
  POST /login                     -> autenticação (JSON {username,password})
  POST /train                     -> dispara treinamento
  POST /predict                   -> dispara geração de predições
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="XAU AI PRO API", version="2.0.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "database" / "trading.db"
PREDICTIONS_DIR = PROJECT_ROOT / "MQL5" / "Files" / "Data"
PY_DIR = PROJECT_ROOT / "Python"
ULT = PROJECT_ROOT / "Ultimate"

# Tenta carregar auth/config do config_store (se presente)
try:
    sys.path.insert(0, str(ULT))
    import config_store as cs
except Exception:
    cs = None

# Sentry (v1.2.2-integration): monitoramento tolerante - nao quebra se nao configurado
try:
    _py_dir = Path(__file__).resolve().parent.parent / "Python"
    sys.path.insert(0, str(_py_dir))
    from sentry_config import init_sentry
    init_sentry()
except Exception:
    pass


# ============================================================
# MODELOS
# ============================================================
class LoginBody(BaseModel):
    username: str
    password: str


# ============================================================
# HELPERS
# ============================================================
def _market() -> object | None:
    """Retorna uma instância do MarketLive (ou None se indisponível)."""
    try:
        sys.path.insert(0, str(ULT))
        import market_live as ml

        return ml.MarketLive()
    except Exception:
        return None


def _py() -> str:
    return sys.executable or "python"


def _read_prediction_file(symbol: str) -> dict:
    """Lê e retorna o conteúdo do arquivo de predição de forma segura.
    
    Usa whitelist estrita e verificação de contenção para prevenir path traversal.
    Retorna o conteúdo do arquivo como dict.
    """
    # Normaliza o símbolo
    normalized = symbol.strip().upper()
    
    # Validação de tamanho
    if not normalized or len(normalized) > 64:
        raise ValueError("Invalid symbol")
    
    # Whitelist estrita: apenas A-Z, 0-9 e underscore
    if not re.fullmatch(r"[A-Z0-9_]+", normalized):
        raise ValueError("Invalid symbol")
    
    # Diretório base confiável (resolvido uma vez)
    base_dir = os.path.realpath(str(PREDICTIONS_DIR.resolve()))
    
    # Constrói o filename de forma segura
    filename = "prediction_" + normalized + ".json"
    
    # Usa os.path.join para construir o path (mais seguro que /)
    full_path = os.path.join(base_dir, filename)
    
    # Resolve o path final
    real_path = os.path.realpath(full_path)
    
    # Verificação de contenção: o path deve estar dentro do diretório base
    # Usa os.path.commonpath para comparação segura
    if os.path.commonpath([real_path, base_dir]) != base_dir:
        raise ValueError("Invalid symbol")
    
    # Lê o arquivo
    try:
        with open(real_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Error reading file: {e}")


# ============================================================
# ROTAS
# ============================================================
@app.get("/")
def read_root():
    return {"status": "online", "app": "XAU AI PRO API", "version": "2.0.0"}


@app.get("/prediction/{symbol}")
def get_prediction(symbol: str):
    try:
        return _read_prediction_file(symbol)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Prediction not found")


@app.get("/predictions")
def list_predictions():
    out = []
    for p in sorted(PREDICTIONS_DIR.glob("prediction_*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


@app.get("/account")
def get_account():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute("SELECT * FROM account WHERE id=1")
        row = c.fetchone()
        conn.close()
        if row:
            return {"login": row[0], "balance": row[1], "equity": row[2],
                    "margin": row[3]}
        return {"error": "Account not found"}
    except Exception:
        return {"error": "Database error"}


@app.get("/market/live")
def market_live():
    m = _market()
    if m is None:
        raise HTTPException(status_code=503, detail="Market provider unavailable")
    symbols = ["XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "USDJPY"]
    quotes = m.get_many(symbols)
    return {"count": len(quotes), "quotes": quotes}


@app.get("/market/live/{symbol}")
def market_live_symbol(symbol: str):
    m = _market()
    if m is None:
        raise HTTPException(status_code=503, detail="Market provider unavailable")
    q = m.get_quote(symbol)
    if not q:
        raise HTTPException(status_code=404, detail="No quote available")
    return q


@app.post("/login")
def login(body: LoginBody):
    if cs is None:
        raise HTTPException(status_code=500, detail="auth disabled")
    if cs.authenticate(body.username, body.password):
        cs.set_session(body.username)
        return {"ok": True, "user": body.username}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/train")
def train():
    r = subprocess.run([_py(), "train.py"], cwd=str(PY_DIR),
                       capture_output=True, text=True, timeout=1800)
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "output": (r.stdout or "")[-1500:], "error": (r.stderr or "")[-500:]}


@app.post("/predict")
def predict():
    r = subprocess.run([_py(), "predict.py"], cwd=str(PY_DIR),
                       capture_output=True, text=True, timeout=1800)
    return {"ok": r.returncode == 0, "returncode": r.returncode,
            "output": (r.stdout or "")[-1500:], "error": (r.stderr or "")[-500:]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)