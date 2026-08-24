"""
XAU AI PRO - Integracao MetaTrader 5 + Robo (versao completa)

Conecta ao terminal MT5 usando a sessao ja logada (sem pedir senha),
com auto-detecao do caminho, obtencao de conta, posicoes, historico,
status do robo (EA) e gerenciamento manual de ordens.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

TERMINAL_CANDIDATES = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal.exe",
    r"C:\MetaTrader 5\terminal64.exe",
]


def find_terminal_path() -> str | None:
    for p in TERMINAL_CANDIDATES:
        if os.path.exists(p):
            return p
    for base in (r"C:\Program Files", r"C:\Program Files (x86)", r"C:\MetaTrader 5"):
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower() in ("terminal64.exe", "terminal.exe"):
                    return os.path.join(root, f)
            if root.count(os.sep) - base.count(os.sep) >= 2:
                dirs[:] = []
    return None


@dataclass
class MT5Position:
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    profit: float
    swap: float
    commission: float
    magic: int
    open_time: str


@dataclass
class MT5Deal:
    ticket: int
    symbol: str
    type: str
    volume: float
    price: float
    profit: float
    commission: float
    swap: float
    magic: int
    time: str


class MT5Bridge:
    _instance: MT5Bridge | None = None
    _lock = threading.Lock()

    def __new__(cls) -> MT5Bridge:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.mt5: Any = None
        self._connected = False
        self._last_error = ""
        self._initialized = True

    def connect(self, path: str | None = None) -> bool:
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            if self._connected:
                return True
            ok = self.mt5.initialize(path=path) if path else self.mt5.initialize()
            if not ok:
                self._last_error = str(self.mt5.last_error())
                self._connected = False
                return False
            self._connected = True
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = str(e)
            self.mt5 = None
            self._connected = False
            return False

    def connect_with_credentials(self, login: int, password: str, server: str) -> bool:
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            ok = self.mt5.initialize(login=int(login), password=password, server=server)
            if not ok:
                self._last_error = str(self.mt5.last_error())
                self._connected = False
                return False
            self._connected = True
            self._last_error = ""
            return True
        except Exception as e:
            self._last_error = str(e)
            self.mt5 = None
            self._connected = False
            return False

    def is_connected(self) -> bool:
        return self._connected

    def last_error(self) -> str:
        return self._last_error

    def shutdown(self) -> None:
        if self.mt5 is not None and self._connected:
            try:
                self.mt5.shutdown()
            except Exception:
                pass
        self._connected = False

    def account_info(self) -> dict[str, Any] | None:
        if not self._connected or self.mt5 is None:
            return None
        try:
            info = self.mt5.account_info()
            if info is None:
                return None
            return {
                "login": info.login,
                "name": info.name,
                "company": info.company,
                "server": info.server,
                "currency": info.currency,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.margin_free,
                "margin_level": info.margin_level,
                "leverage": info.leverage,
                "profit": info.profit,
            }
        except Exception:
            return None

    def symbols(self) -> list[str]:
        if not self._connected or self.mt5 is None:
            return []
        try:
            syms = self.mt5.symbols_get()
            return [s.name for s in syms] if syms else []
        except Exception:
            return []

    def tick(self, symbol: str) -> dict[str, Any] | None:
        if not self._connected or self.mt5 is None:
            return None
        try:
            t = self.mt5.symbol_info_tick(symbol)
            if t is None:
                return None
            return {
                "symbol": symbol,
                "bid": t.bid,
                "ask": t.ask,
                "last": t.last,
                "time": datetime.fromtimestamp(t.time).strftime("%H:%M:%S"),
            }
        except Exception:
            return None

    def get_positions(self, magic: int | None = None) -> list[MT5Position]:
        if not self._connected or self.mt5 is None:
            return []
        try:
            positions = self.mt5.positions_get()
            if positions is None:
                return []
            result = []
            for p in positions:
                if magic is not None and p.magic != magic:
                    continue
                result.append(
                    MT5Position(
                        ticket=p.ticket,
                        symbol=p.symbol,
                        type="BUY" if p.type == 0 else "SELL",
                        volume=p.volume,
                        open_price=p.price_open,
                        current_price=p.price_current,
                        sl=p.sl,
                        tp=p.tp,
                        profit=p.profit,
                        swap=p.swap,
                        commission=p.commission,
                        magic=p.magic,
                        open_time=datetime.fromtimestamp(p.time).strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )
            return result
        except Exception:
            return []

    def get_history(self, days: int = 7, magic: int | None = None) -> list[MT5Deal]:
        if not self._connected or self.mt5 is None:
            return []
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            deals = self.mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            result = []
            for d in deals:
                if magic is not None and d.magic != magic:
                    continue
                result.append(
                    MT5Deal(
                        ticket=d.ticket,
                        symbol=d.symbol,
                        type="BUY" if d.type == 0 else "SELL",
                        volume=d.volume,
                        price=d.price,
                        profit=d.profit,
                        commission=d.commission,
                        swap=d.swap,
                        magic=d.magic,
                        time=datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )
            return result
        except Exception:
            return []

    def send_order(self, symbol: str, order_type: str, volume: float,
                   sl: float = 0.0, tp: float = 0.0, magic: int = 2026001,
                   comment: str = "XAU_AI_PRO") -> dict[str, Any]:
        if not self._connected or self.mt5 is None:
            return {"ok": False, "error": "MT5 nao conectado"}
        try:
            import MetaTrader5 as mt5
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"ok": False, "error": f"Simbolo {symbol} nao encontrado"}
            price = tick.ask if order_type.upper() == "BUY" else tick.bid
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL,
                "price": price,
                "deviation": 10,
                "magic": int(magic),
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            if sl > 0:
                request["sl"] = sl
            if tp > 0:
                request["tp"] = tp
            result = self.mt5.order_send(request)
            if result is None:
                return {"ok": False, "error": str(self.mt5.last_error())}
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"ok": True, "ticket": result.order, "price": result.price}
            return {"ok": False, "error": f"Retcode {result.retcode}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def close_position(self, ticket: int) -> dict[str, Any]:
        if not self._connected or self.mt5 is None:
            return {"ok": False, "error": "MT5 nao conectado"}
        try:
            import MetaTrader5 as mt5
            position = self.mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                return {"ok": False, "error": "Posicao nao encontrada"}
            pos = position[0]
            symbol = pos.symbol
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"ok": False, "error": "Tick nao disponivel"}
            price = tick.bid if pos.type == 0 else tick.ask
            order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 10,
                "magic": pos.magic,
                "comment": "XAU_AI_PRO close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = self.mt5.order_send(request)
            if result is None:
                return {"ok": False, "error": str(self.mt5.last_error())}
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"ok": True, "ticket": result.order, "price": result.price}
            return {"ok": False, "error": f"Retcode {result.retcode}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def robot_status(self, magic: int = 2026001) -> dict[str, Any]:
        if not self._connected or self.mt5 is None:
            return {"active": False, "message": "MT5 nao conectado"}
        try:
            positions = self.mt5.positions_get(magic=magic)
            terminal = self.mt5.terminal_info()
            connected = terminal.connected if terminal else False
            return {
                "active": connected,
                "connected": connected,
                "positions_with_magic": len(positions) if positions else 0,
                "message": "Robo detectado (EA ativo)" if connected else "Nao foi possivel confirmar EA ativo",
            }
        except Exception as e:
            return {"active": False, "message": str(e)}


_bridge = MT5Bridge()


def connect_mt5(path: str | None = None) -> bool:
    if path and os.path.exists(path):
        return _bridge.connect(path=path)
    detected = find_terminal_path()
    if detected:
        return _bridge.connect(path=detected)
    return _bridge.connect()


def disconnect_mt5() -> None:
    _bridge.shutdown()


def get_account_info() -> dict[str, Any] | None:
    return _bridge.account_info()


def get_positions(magic: int | None = 2026001) -> list[MT5Position]:
    return _bridge.get_positions(magic=magic)


def get_history(days: int = 7, magic: int | None = 2026001) -> list[MT5Deal]:
    return _bridge.get_history(days=days, magic=magic)


def send_order(symbol: str, order_type: str, volume: float,
               sl: float = 0.0, tp: float = 0.0, magic: int = 2026001) -> dict[str, Any]:
    return _bridge.send_order(symbol, order_type, volume, sl, tp, magic)


def close_position(ticket: int) -> dict[str, Any]:
    return _bridge.close_position(ticket)


def start_robot() -> bool:
    return connect_mt5()


def stop_robot() -> bool:
    disconnect_mt5()
    return True


def robot_status() -> str:
    status = _bridge.robot_status()
    return status.get("message", "desconhecido")


def sync_account_to_db(db_path: Path | None = None) -> bool:
    try:
        from config_store import DB_PATH
        db_path = db_path or DB_PATH
        info = get_account_info()
        if info is None:
            return False
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS account(
                id INTEGER PRIMARY KEY,
                login TEXT, balance REAL, equity REAL, margin REAL,
                company TEXT, server TEXT
            )
            """
        )
        c.execute(
            "INSERT OR REPLACE INTO account(id, login, balance, equity, margin, company, server) VALUES(1,?,?,?,?,?,?)",
            (
                str(info.get("login", "")),
                info.get("balance", 0.0),
                info.get("equity", 0.0),
                info.get("margin", 0.0),
                info.get("company", ""),
                info.get("server", ""),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
