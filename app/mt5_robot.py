# -*- coding: utf-8 -*-
"""
Integracao real entre o app Python e o Robo MQL5 no MetaTrader 5.
A API do MT5 nao permite ligar/desligar um EA; o controle e feito via conexao,
deteccao de atividade (magic + posicoes + predicoes), ordens manuais e sync.
"""
from __future__ import annotations

import os
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.config_manager import get_config
from app.mt5_lock import mt5_lock
from app.utils.paths import get_mql_data_path, get_python_dir


TERMINAL_CANDIDATES = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
    r"C:\Program Files (x86)\MetaTrader 5\terminal.exe",
    r"C:\MetaTrader 5\terminal64.exe",
]


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


class MT5Robot:
    def __init__(self) -> None:
        self.mt5: Any = None
        self.connected = False
        self.last_error = ""
        self._lock = threading.Lock()

    def find_terminal(self) -> str | None:
        cfg_path = get_config().get("mt5", "terminal_path", default="")
        if cfg_path and os.path.exists(cfg_path):
            return cfg_path
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

    def connect(self, path: str | None = None) -> bool:
        with self._lock, mt5_lock:
            try:
                import MetaTrader5 as mt5
                self.mt5 = mt5
                if self.connected:
                    return True
                if path:
                    ok = self.mt5.initialize(path=path)
                else:
                    detected = self.find_terminal()
                    ok = self.mt5.initialize(path=detected) if detected else self.mt5.initialize()
                if not ok:
                    self.last_error = str(self.mt5.last_error())
                    self.connected = False
                    return False
                self.connected = True
                self.last_error = ""
                return True
            except Exception as e:
                self.last_error = str(e)
                self.connected = False
                return False

    def disconnect(self) -> None:
        # Nao chamamos mt5.shutdown(): a conexao IPC e compartilhada por todo
        # o processo (MarketData, graficos, busca) e o shutdown a derrubaria.
        with self._lock:
            self.connected = False

    def account_info(self) -> dict[str, Any] | None:
        if not self.connected or not self.mt5:
            return None
        try:
            with mt5_lock:
                info = self.mt5.account_info()
                if info is None:
                    return None
                terminal = self.mt5.terminal_info()
            trade_allowed = bool(terminal.trade_allowed) if terminal else False
            terminal_connected = bool(terminal.connected) if terminal else False
            return {
                "login": info.login,
                "name": info.name,
                "company": info.company,
                "server": info.server,
                "balance": float(info.balance),
                "equity": float(info.equity),
                "margin": float(info.margin),
                "margin_free": float(info.margin_free),
                "margin_level": float(info.margin_level) if info.margin_level else 0.0,
                "profit": float(info.profit),
                "currency": info.currency,
                "trade_allowed": trade_allowed,
                "terminal_connected": terminal_connected,
            }
        except Exception as e:
            self.last_error = str(e)
            return None

    def get_positions(self, magic: int | None = None) -> list[MT5Position]:
        if not self.connected or not self.mt5:
            return []
        try:
            with mt5_lock:
                positions = self.mt5.positions_get()
            if positions is None:
                return []
            result = []
            for p in positions:
                if magic is not None and p.magic != magic:
                    continue
                result.append(MT5Position(
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
                    commission=getattr(p, "commission", 0.0),
                    magic=p.magic,
                    open_time=datetime.fromtimestamp(p.time).strftime("%Y-%m-%d %H:%M:%S"),
                ))
            return result
        except Exception as e:
            self.last_error = str(e)
            return []

    def get_history(self, days: int = 7, magic: int | None = None) -> list[MT5Deal]:
        if not self.connected or not self.mt5:
            return []
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            with mt5_lock:
                deals = self.mt5.history_deals_get(from_date, to_date)
            if deals is None:
                return []
            result = []
            for d in deals:
                if magic is not None and d.magic != magic:
                    continue
                result.append(MT5Deal(
                    ticket=d.ticket,
                    symbol=d.symbol,
                    type="BUY" if d.type == 0 else "SELL",
                    volume=d.volume,
                    price=d.price,
                    profit=d.profit,
                    commission=getattr(d, "commission", 0.0),
                    swap=d.swap,
                    magic=d.magic,
                    time=datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S"),
                ))
            return result
        except Exception as e:
            self.last_error = str(e)
            return []

    def _filling_mode(self) -> Any:
        filling = get_config().get("mt5", "filling_mode", default="ioc")
        return {
            "ioc": self.mt5.ORDER_FILLING_IOC,
            "fok": self.mt5.ORDER_FILLING_FOK,
            "return": self.mt5.ORDER_FILLING_RETURN,
        }.get(filling, self.mt5.ORDER_FILLING_IOC)

    def send_order(self, symbol: str, side: str, volume: float,
                   sl: float = 0.0, tp: float = 0.0,
                   comment: str = "XAU_AI_PRO") -> dict[str, Any]:
        if not self.connected or not self.mt5:
            return {"ok": False, "error": "MT5 nao conectado"}
        try:
            magic = get_config().get("mt5", "magic_number", default=2026001)
            with mt5_lock:
                tick = self.mt5.symbol_info_tick(symbol)
                info = self.mt5.symbol_info(symbol)
            if tick is None or info is None:
                return {"ok": False, "error": f"Simbolo {symbol} nao encontrado"}
            is_buy = side.upper() == "BUY"
            price = tick.ask if is_buy else tick.bid
            order_type = self.mt5.ORDER_TYPE_BUY if is_buy else self.mt5.ORDER_TYPE_SELL
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(volume),
                "type": order_type,
                "price": price,
                "deviation": 10,
                "magic": magic,
                "comment": comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self._filling_mode(),
            }
            if sl > 0:
                request["sl"] = sl
            if tp > 0:
                request["tp"] = tp
            with mt5_lock:
                result = self.mt5.order_send(request)
                if result is None:
                    return {"ok": False, "error": str(self.mt5.last_error())}
                if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                    return {"ok": True, "ticket": result.order, "price": result.price, "volume": volume}
                return {"ok": False, "error": f"Retcode {result.retcode}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def close_position(self, ticket: int) -> dict[str, Any]:
        if not self.connected or not self.mt5:
            return {"ok": False, "error": "MT5 nao conectado"}
        try:
            with mt5_lock:
                position = self.mt5.positions_get(ticket=ticket)
            if not position:
                return {"ok": False, "error": "Posicao nao encontrada"}
            pos = position[0]
            symbol = pos.symbol
            with mt5_lock:
                tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                return {"ok": False, "error": "Tick nao disponivel"}
            price = tick.bid if pos.type == 0 else tick.ask
            order_type = self.mt5.ORDER_TYPE_SELL if pos.type == 0 else self.mt5.ORDER_TYPE_BUY
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": pos.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 10,
                "magic": pos.magic,
                "comment": "XAU_AI_PRO close",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self._filling_mode(),
            }
            with mt5_lock:
                result = self.mt5.order_send(request)
                if result is None:
                    return {"ok": False, "error": str(self.mt5.last_error())}
                if result.retcode == self.mt5.TRADE_RETCODE_DONE:
                    return {"ok": True, "ticket": result.order, "price": result.price}
                return {"ok": False, "error": f"Retcode {result.retcode}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


    def close_all_positions(self, magic: int | None = None) -> dict[str, Any]:
        if not self.connected or not self.mt5:
            return {"ok": False, "error": "MT5 nao conectado"}
        positions = self.get_positions(magic=magic)
        closed = 0
        errors = []
        for pos in positions:
            res = self.close_position(pos.ticket)
            if res.get("ok"):
                closed += 1
            else:
                errors.append(f"#{pos.ticket}: {res.get('error')}")
        return {"ok": closed > 0, "closed": closed, "errors": errors}

    def cancel_pending_orders(self, magic: int | None = None) -> dict[str, Any]:
        """Cancela todas as ordens pendentes (com ou sem filtro de magic)."""
        if not self.connected or not self.mt5:
            return {"ok": False, "error": "MT5 nao conectado"}
        try:
            with mt5_lock:
                orders = self.mt5.orders_get()
            canceled = 0
            errors = []
            for order in orders or []:
                if magic is not None and order.magic != magic:
                    continue
                try:
                    with mt5_lock:
                        result = self.mt5.order_delete(order.ticket)
                    if result and result.retcode == self.mt5.TRADE_RETCODE_DONE:
                        canceled += 1
                    else:
                        errors.append(f"#{order.ticket}: {getattr(result, 'comment', 'sem retorno')}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"#{order.ticket}: {exc}")
            return {"ok": True, "canceled": canceled, "errors": errors}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def is_ea_active(self, magic: int | None = None) -> dict[str, Any]:
        """Detecta se o EA está ativo usando heartbeat como critério primário.

        Estratégia:
        1. Heartbeat (system_status.json) - critério primário (detecta EA ligado sem operar)
        2. Posições com magic + predições recentes - fallback/reduncia
        """
        # 1. Validação primária: heartbeat do system_status.json
        try:
            from app.system_status_reader import read_system_status
            status = read_system_status()
            if status and status.get("ea_online"):
                return {
                    "active": True,
                    "connected": True,
                    "heartbeat_age_sec": status.get("heartbeat_age_sec", -1),
                    "positions_with_magic": 0,
                    "predictions_recent": False,
                    "reason": f"EA online (heartbeat {status.get('heartbeat_age_sec', '?')}s)",
                }
        except Exception:
            pass  # Fallback para verificação heurística

        # 2. Fallback: MT5 direto (posições + predições)
        if not self.connected or not self.mt5:
            return {"active": False, "reason": "MT5 nao conectado"}
        try:
            with mt5_lock:
                terminal = self.mt5.terminal_info()
            connected = terminal.connected if terminal else False
            if not connected:
                return {"active": False, "reason": "Terminal MT5 desconectado"}
            magic = magic or get_config().get("mt5", "magic_number", default=2026001)
            with mt5_lock:
                positions = self.mt5.positions_get(magic=magic)
            positions_count = len(positions) if positions else 0
            predictions_active = self._check_recent_predictions()
            active = positions_count > 0 or predictions_active
            return {
                "active": active,
                "connected": True,
                "positions_with_magic": positions_count,
                "predictions_recent": predictions_active,
                "reason": "EA ativo (posicoes ou predicoes recentes)" if active else "Nenhuma atividade do EA detectada",
            }
        except Exception as e:
            return {"active": False, "reason": str(e)}

    def _check_recent_predictions(self, max_age_seconds: int = 600) -> bool:
        mql_data = get_mql_data_path()
        now = time.time()
        for f in mql_data.glob("prediction_*.json"):
            try:
                mtime = os.path.getmtime(f)
                if now - mtime <= max_age_seconds:
                    return True
            except Exception:
                continue
        return False

    def sync_predictions(self) -> dict[str, Any]:
        try:
            src_dir = get_python_dir() / "ai"
            dst_dir = get_mql_data_path()
            dst_dir.mkdir(parents=True, exist_ok=True)
            copied = 0
            for src in src_dir.glob("prediction*.json"):
                dst = dst_dir / src.name
                shutil.copy2(src, dst)
                copied += 1
            return {"ok": True, "copied": copied}
        except Exception as e:
            return {"ok": False, "error": str(e)}


_robot: MT5Robot | None = None


def get_robot() -> MT5Robot:
    global _robot
    if _robot is None:
        _robot = MT5Robot()
    return _robot

