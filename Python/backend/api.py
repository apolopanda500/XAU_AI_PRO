"""
XAU AI PRO - API Backend (FastAPI)
Endpoints:
  GET  /                          -> status
  GET  /health                    -> health (alias de /)
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
import sqlite3
import subprocess
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="XAU AI PRO API", version="1.2.0")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from app.utils.paths import get_mql_data_path

DATA_DIR = get_mql_data_path()
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

DB_PATH = PROJECT_ROOT / "database" / "trading.db"
PREDICTIONS_DIR = DATA_DIR
PY_DIR = PROJECT_ROOT / "Python"
ULT = PROJECT_ROOT / "Ultimate"

# Tenta carregar auth/config do config_store (se presente)
try:
    sys.path.insert(0, str(ULT))
    import config_store as cs
except Exception:
    cs = None


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



def _prediction_file(symbol: str) -> Path:
    """Retorna o path seguro de predição para um símbolo (evita path traversal).
    
    Validação:
    1. Normaliza para uppercase e strip
    2. Verifica tamanho (1-64 chars)
    3. Whitelist: apenas A-Z, 0-9 e underscore
    4. Resolve o path e verifica contenção no diretório base
    """
    normalized = symbol.strip().upper()
    if not normalized or len(normalized) > 64:
        raise ValueError("Invalid symbol")
    # Whitelist estrita: apenas caracteres seguros para filenames
    if not normalized.replace("_", "").isalnum():
        raise ValueError("Invalid symbol")
    base = PREDICTIONS_DIR.resolve()
    # Constrói path sem f-string com input do usuário
    filename = "prediction_" + normalized + ".json"
    path = base / filename
    # Verifica contenção (path traversal protection)
    real_base = str(base.resolve())
    real_path = str(Path(path).resolve())
    if not real_path.startswith(real_base + os.sep) and real_path != real_base:
        raise ValueError("Invalid symbol")
    return Path(real_path)


# ============================================================
# ROTAS
# ============================================================
@app.get("/")
def read_root():
    return {"status": "online", "app": "XAU AI PRO API", "version": "1.2.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/prediction/{symbol}")
def get_prediction(symbol: str):
    try:
        path = _prediction_file(symbol)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid symbol")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Prediction not found")
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="Error reading prediction")


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
    uvicorn.run(
        app,
        host=os.getenv("XAU_AI_PRO_API_HOST", "127.0.0.1"),
        port=int(os.getenv("XAU_AI_PRO_API_PORT", "8000")),
    )
