# -*- coding: utf-8 -*-
"""Guardian Engine - gestao continua de posicoes DEMO (Fase 1 do gap analysis).

Monitora posicoes a cada tick e executa automaticamente:
  - Breakeven automatico (SL -> entrada + offset) apos gatilho de lucro
  - Trailing stop: fixed (distancia fixa), step (com passo minimo) e ATR
  - Parciais TP1/TP2/TP3 (partial close por gatilho de distancia ou lucro)
  - Profit lock (trava pico de lucro com devolucao maxima)
  - Time exit (tempo maximo em minutos ou horario de fechamento)

Seguranca: o motor NAO possui caminho proprio de ordens. Toda acao e executada
exclusivamente pelas funcoes _demo_* do mt5_gateway, herdando as travas
XAU_ENABLE_DEMO_ORDERS=1, confirm_demo=true e conta somente-DEMO. Com a parada
de emergencia (REAL_EMERGENCY_STOP) ativa, o motor pausa toda execucao.

Rodar: importado pelo gateway; loop inicia com start_guardian_loop().
"""
from __future__ import annotations

import json
import os
import threading
import time
import math
from datetime import datetime, timedelta
from pathlib import Path

from backend import intent_log
from backend import watchdog as _watchdog

INTERVAL_SEC = float(os.getenv("XAU_GUARDIAN_INTERVAL", "1.0") or 1.0)
RULES_FILE = Path(os.getenv("XAU_GUARDIAN_FILE", str(
    Path(os.environ.get("APPDATA", "")) / "XAU_AI_PRO" / "guardian_rules.json")))

_LOCK = threading.RLock()
RULES: dict[int, dict] = {}          # ticket -> regra validada
STATE: dict[int, dict] = {}          # ticket -> estado runtime (picos, parciais executadas)
_TICK_INFO: dict = {"last_tick": None, "actions": [], "error": None, "emergency_stop": False}
_LOOP_STARTED = False
_ATR_CACHE: dict[str, tuple[float, float]] = {}  # symbol:config -> (ts, atr)
_SYMBOL_CACHE: dict[str, tuple[float, dict]] = {}  # symbol -> (ts, meta)

TF_MAP = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 16385, "H4": 16388, "D1": 16408}


def _now_iso() -> str:
    return datetime.now().isoformat()


def _num(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def _load_rules() -> None:
    """Carrega regras persistidas (best-effort; arquivo corrompido e ignorado)."""
    try:
        if RULES_FILE.exists():
            data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
            for ticket, rule in (data.get("rules") or {}).items():
                RULES[int(ticket)] = rule
            for ticket, st in (data.get("state") or {}).items():
                STATE[int(ticket)] = st
    except Exception:
        pass


def _save_rules() -> None:
    try:
        RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        RULES_FILE.write_text(json.dumps(
            {"rules": {str(k): v for k, v in RULES.items()},
             "state": {str(k): v for k, v in STATE.items()},
             "updated_at": _now_iso()}, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _emergency_stop() -> bool:
    from backend import mt5_gateway as gw
    return gw.REAL_EMERGENCY_STOP.exists()


def _symbol_meta(mt5, symbol: str) -> dict:
    """Cache curto de point/stops_level/volume_min/step/digits por simbolo."""
    now = time.time()
    cached = _SYMBOL_CACHE.get(symbol)
    if cached and now - cached[0] < 5.0:
        return cached[1]
    info = mt5.symbol_info(symbol)
    meta = {
        "point": _num(getattr(info, "point", 0.0)),
        "stops_level": int(_num(getattr(info, "trade_stops_level", 0))),
        "volume_min": _num(getattr(info, "volume_min", 0.01), 0.01),
        "volume_step": _num(getattr(info, "volume_step", 0.01), 0.01),
        "digits": int(_num(getattr(info, "digits", 2), 2)),
    }
    _SYMBOL_CACHE[symbol] = (now, meta)
    return meta


def _atr(mt5, symbol: str, period: int, tf: str) -> float:
    """ATR real via copy_rates_from_pos; cache de 30s por simbolo/config."""
    period = max(2, min(int(period or 14), 200))
    tf_code = TF_MAP.get(str(tf or "M5").upper(), 5)
    key = f"{symbol}:{period}:{tf_code}"
    now = time.time()
    cached = _ATR_CACHE.get(key)
    if cached and now - cached[0] < 30.0:
        return cached[1]
    try:
        rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, period + 1)
    except Exception:
        rates = None
    if not rates or len(rates) < 2:
        return 0.0
    trs = []
    for i in range(1, len(rates)):
        high, low = float(rates[i]["high"]), float(rates[i]["low"])
        prev_close = float(rates[i - 1]["close"])
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    atr_value = sum(trs) / len(trs) if trs else 0.0
    _ATR_CACHE[key] = (now, atr_value)
    return atr_value


def _round_vol(volume: float, meta: dict) -> float:
    step = meta.get("volume_step") or 0.01
    if step <= 0:
        step = 0.01
    return max(meta.get("volume_min", 0.01), round(volume / step) * step)


def _trigger_hit(item: dict, profit: float, gain_distance: float) -> bool:
    """Gatilho por distancia de preco ('trigger') OU lucro em moeda ('trigger_profit')."""
    trig_profit = _num(item.get("trigger_profit"), 0.0)
    trig_dist = _num(item.get("trigger"), 0.0)
    if trig_profit > 0:
        return profit >= trig_profit
    if trig_dist > 0:
        return gain_distance >= trig_dist
    return False


def _normalize_rule(payload: dict) -> dict:
    """Valida e normaliza a regra enviada pelo painel."""
    ticket = int(_num(payload.get("ticket"), 0))
    if ticket <= 0:
        raise ValueError("ticket obrigatorio")
    rule: dict = {"ticket": ticket, "created_at": _now_iso()}
    breakeven = payload.get("breakeven") or {}
    if _num(breakeven.get("trigger"), 0) > 0 or _num(breakeven.get("trigger_profit"), 0) > 0:
        rule["breakeven"] = {
            "trigger": _num(breakeven.get("trigger"), 0.0),
            "trigger_profit": _num(breakeven.get("trigger_profit"), 0.0),
            "offset": max(0.0, _num(breakeven.get("offset"), 0.0)),
        }
    trailing = payload.get("trailing") or {}
    mode = str(trailing.get("mode", "")).strip().lower()
    if mode in {"fixed", "step", "atr"}:
        rule["trailing"] = {
            "mode": mode,
            "distance": max(0.0, _num(trailing.get("distance"), 0.0)),
            "step": max(0.0, _num(trailing.get("step"), 0.0)),
            "atr_period": int(max(2, min(_num(trailing.get("atr_period"), 14), 200))),
            "atr_tf": str(trailing.get("atr_tf", "M5")).upper(),
            "atr_multiplier": max(0.1, _num(trailing.get("atr_multiplier"), 2.0)),
        }
        if mode in {"fixed", "step"} and rule["trailing"]["distance"] <= 0:
            raise ValueError("trailing.fixed/step exige distance > 0")
    clean_partials = []
    for item in (payload.get("partials") or [])[:3]:
        trigger = _num(item.get("trigger"), 0.0)
        trigger_profit = _num(item.get("trigger_profit"), 0.0)
        volume = _num(item.get("volume"), 0.0)
        if (trigger <= 0 and trigger_profit <= 0) or volume <= 0:
            continue
        clean_partials.append({"trigger": trigger, "trigger_profit": trigger_profit,
                               "volume": volume})
    if clean_partials:
        rule["partials"] = clean_partials
    profit_lock = payload.get("profit_lock") or {}
    if _num(profit_lock.get("trigger"), 0) > 0 or _num(profit_lock.get("trigger_profit"), 0) > 0:
        rule["profit_lock"] = {
            "trigger": _num(profit_lock.get("trigger"), 0.0),
            "trigger_profit": _num(profit_lock.get("trigger_profit"), 0.0),
            "giveback": max(0.0, _num(profit_lock.get("giveback"), 0.0)),
        }
    time_exit = payload.get("time_exit") or {}
    minutes = _num(time_exit.get("max_minutes"), 0.0)
    close_at = str(time_exit.get("close_at", "")).strip()
    if minutes > 0 or close_at:
        rule["time_exit"] = {"max_minutes": minutes, "close_at": close_at,
                             "only_if_loss": bool(time_exit.get("only_if_loss", False))}
    if not any(k in rule for k in ("breakeven", "trailing", "partials", "profit_lock", "time_exit")):
        raise ValueError("configure ao menos um modulo (breakeven, trailing, partials, profit_lock ou time_exit)")
    return rule


def guardian_set(payload: dict) -> dict:
    """Ativa/atualiza regra de guardian para um ticket (somente DEMO)."""
    from backend import mt5_gateway as gw
    payload = {**payload, "confirm_demo": True}
    mt5, _ = gw._require_demo_command(payload)
    ticket = int(_num(payload.get("ticket"), 0))
    rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows:
        raise LookupError("posicao DEMO nao encontrada para o guardian")
    pos = rows[0]
    rule = _normalize_rule(payload)
    symbol = str(getattr(pos, "symbol", ""))
    rule["symbol"] = symbol
    rule["side"] = "BUY" if getattr(pos, "type", 0) == 0 else "SELL"
    opened_iso = ""
    pos_time = _num(getattr(pos, "time", 0.0), 0.0)
    if pos_time > 0:
        try:
            opened_iso = datetime.fromtimestamp(pos_time).isoformat()
        except (OSError, OverflowError, ValueError):
            opened_iso = ""
    with _LOCK:
        previous = RULES.get(ticket)
        RULES[ticket] = rule
        st = STATE.get(ticket) or {}
        if not previous:
            st = {"executed_partials": [], "peak_distance": 0.0, "peak_profit": 0.0,
                  "breakeven_done": False, "opened_at": opened_iso or _now_iso(),
                  "position_time": opened_iso}
        elif (previous.get("partials") or []) != (rule.get("partials") or []):
            st["executed_partials"] = []
        if opened_iso:
            st["position_time"] = opened_iso
            if not st.get("opened_at") or "position_time" in st:
                st["opened_at"] = opened_iso
        STATE[ticket] = st
        _save_rules()
    intent_log.record_intent("guardian_set",
                             {"ticket": ticket, "symbol": symbol, "rule": rule},
                             status="sent")
    _watchdog.record("guardian_set", {"ticket": ticket, "symbol": symbol})
    return {"ok": True, "guardian": "active", "ticket": ticket, "symbol": symbol,
            "rule": rule, "demo_only": True}


def guardian_remove(payload: dict) -> dict:
    """Remove a regra do guardian para um ticket (posicao continua aberta)."""
    from backend import mt5_gateway as gw
    payload = {**payload, "confirm_demo": True}
    gw._require_demo_command(payload)
    ticket = int(_num(payload.get("ticket"), 0))
    with _LOCK:
        removed = RULES.pop(ticket, None)
        STATE.pop(ticket, None)
        _save_rules()
    if not removed:
        raise LookupError("nenhuma regra guardian ativa para este ticket")
    return {"ok": True, "guardian": "removed", "ticket": ticket}


def guardian_status() -> dict:
    from backend import mt5_gateway as gw
    with _LOCK:
        rules = {str(t): dict(r) for t, r in RULES.items()}
        state = {str(t): dict(s) for t, s in STATE.items()}
    emergency = _emergency_stop()
    demo_enabled = os.getenv("XAU_ENABLE_DEMO_ORDERS", "0") == "1"
    if emergency:
        engine = "paused_emergency_stop"
    elif not demo_enabled:
        engine = "blocked_demo_orders"
    else:
        engine = "enabled"
    return {"ok": True, "guardian": engine, "demo_only": True,
            "interval_sec": INTERVAL_SEC, "rules": rules, "state": state,
            "count": len(rules), "last_tick": _TICK_INFO.get("last_tick"),
            "last_actions": _TICK_INFO.get("actions", [])[-20:],
            "last_error": _TICK_INFO.get("error"),
            "emergency_stop": emergency, "source": "guardian_engine"}


def _sl_would_tighten(side: str, new_sl: float, current_sl: float) -> bool:
    """SL so pode se mover a favor da posicao (nunca afrouxa a protecao)."""
    if new_sl <= 0:
        return False
    if current_sl <= 0:
        return True
    return new_sl > current_sl if side == "BUY" else new_sl < current_sl


def _send_sltp(gw, mt5, pos, sl: float, tp: float) -> dict:
    ticket_sltp = int(getattr(pos, "ticket", 0))
    request = {"action": mt5.TRADE_ACTION_SLTP, "symbol": str(getattr(pos, "symbol", "")),
               "position": ticket_sltp, "sl": sl, "tp": tp}
    result = mt5.order_send(request)
    ok = bool(result and getattr(result, "retcode", 0) == mt5.TRADE_RETCODE_DONE)
    intent_log.record_intent("guardian_sltp", {"ticket": ticket_sltp, "sl": sl, "tp": tp,
                                               "symbol": str(getattr(pos, "symbol", ""))},
                             status="sent" if ok else "failed",
                             extra={"retcode": int(getattr(result, "retcode", -1))})
    return {"ok": ok, "sl": sl, "tp": tp, "retcode": int(getattr(result, "retcode", -1))}


def _guard_tick_rule(gw, mt5, ticket: int, rule: dict, actions: list) -> None:
    rows = mt5.positions_get(ticket=ticket) if ticket else None
    if not rows:
        actions.append({"ticket": ticket, "action": "auto_remove", "reason": "posicao fechada"})
        with _LOCK:
            RULES.pop(ticket, None)
            STATE.pop(ticket, None)
            _save_rules()
        return
    pos = rows[0]
    side = "BUY" if getattr(pos, "type", 0) == 0 else "SELL"
    symbol = str(getattr(pos, "symbol", ""))
    entry = float(getattr(pos, "price_open", 0.0) or 0.0)
    current_sl = float(getattr(pos, "sl", 0.0) or 0.0)
    current_tp = float(getattr(pos, "tp", 0.0) or 0.0)
    profit = float(getattr(pos, "profit", 0.0) or 0.0)
    volume = float(getattr(pos, "volume", 0.0) or 0.0)
    tick = mt5.symbol_info_tick(symbol)
    if not tick or entry <= 0:
        return
    market = float(tick.bid if side == "BUY" else tick.ask)
    meta = _symbol_meta(mt5, symbol)
    min_dist = (meta.get("stops_level", 0) * meta.get("point", 0.0)) or 0.0
    gain = (market - entry) if side == "BUY" else (entry - market)
    pos_time = _num(getattr(pos, "time", 0.0), 0.0)
    if pos_time > 0:
        try:
            st["position_time"] = datetime.fromtimestamp(pos_time).isoformat()
            st["opened_at"] = st["position_time"]  # tempo REAL de abertura da posicao
        except (OSError, OverflowError, ValueError):
            pass
    st = STATE.setdefault(ticket, {"executed_partials": [], "peak_distance": 0.0,
                                   "peak_profit": 0.0, "breakeven_done": False,
                                   "opened_at": _now_iso()})
    st["peak_distance"] = max(_num(st.get("peak_distance"), 0.0), gain)
    st["peak_profit"] = max(_num(st.get("peak_profit"), 0.0), profit)

    # 1) Parciais TP1/TP2/TP3 (antes de mexer no SL; volume muda a referencia)
    for idx, item in enumerate(rule.get("partials", [])):
        if idx in st.get("executed_partials", []):
            continue
        if not _trigger_hit(item, profit, gain):
            continue
        part = _round_vol(_num(item.get("volume"), 0.0), meta)
        if part >= volume:
            actions.append({"ticket": ticket, "action": f"partial[{idx}]_skipped",
                            "reason": "volume >= posicao"})
            st.setdefault("executed_partials", []).append(idx)
            continue
        try:
            result = gw._demo_partial_close({"ticket": ticket, "volume": part, "confirm_demo": True})
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        intent_log.record_intent("guardian_partial",
                                 {"ticket": ticket, "index": idx, "volume": part, "symbol": rule.get("symbol", "")},
                                 status="sent" if result.get("ok") else "failed",
                                 extra={"retcode": result.get("retcode"), "error": result.get("error")})
        actions.append({"ticket": ticket, "action": f"partial[{idx}]", "volume": part,
                        "ok": bool(result.get("ok"))})
        if result.get("ok"):
            st.setdefault("executed_partials", []).append(idx)
            rows = mt5.positions_get(ticket=ticket) if ticket else None
            if not rows:
                with _LOCK:
                    RULES.pop(ticket, None); STATE.pop(ticket, None); _save_rules()
                return
            pos = rows[0]
            volume = float(getattr(pos, "volume", 0.0) or 0.0)
            profit = float(getattr(pos, "profit", 0.0) or 0.0)

    # 2) Breakeven automatico
    be = rule.get("breakeven")
    if be and not st.get("breakeven_done") and _trigger_hit(be, profit, gain):
        target = round(entry + be.get("offset", 0.0) if side == "BUY"
                       else entry - be.get("offset", 0.0), meta.get("digits", 2))
        if _sl_would_tighten(side, target, current_sl) and abs(target - market) >= min_dist:
            result = _send_sltp(gw, mt5, pos, target, current_tp)
            actions.append({"ticket": ticket, "action": "breakeven", "sl": target,
                            "ok": result["ok"]})
            if result["ok"]:
                st["breakeven_done"] = True
                current_sl = target
        else:
            st["breakeven_done"] = True  # respeita stops level; nao insiste neste tick

    # 3) Profit lock (trava o pico de lucro com devolucao maxima)
    pl = rule.get("profit_lock")
    if pl:
        peak_d = _num(st.get("peak_distance"), 0.0)
        trigger_d = _num(pl.get("trigger"), 0.0)
        trigger_p = _num(pl.get("trigger_profit"), 0.0)
        if (trigger_p > 0 and _num(st.get("peak_profit"), 0.0) >= trigger_p) or \
           (trigger_d > 0 and peak_d >= trigger_d):
            locked = peak_d - _num(pl.get("giveback"), 0.0)
            target = round(entry + locked if side == "BUY" else entry - locked,
                           meta.get("digits", 2))
            if _sl_would_tighten(side, target, current_sl) and abs(target - market) >= min_dist:
                result = _send_sltp(gw, mt5, pos, target, current_tp)
                actions.append({"ticket": ticket, "action": "profit_lock", "sl": target,
                                "ok": result["ok"]})
                if result["ok"]:
                    current_sl = target

    # 4) Trailing stop (fixed / step / atr) - nunca afrouxa o SL
    tr = rule.get("trailing")
    if tr:
        if tr["mode"] == "atr":
            distance = _atr(mt5, symbol, tr.get("atr_period", 14), tr.get("atr_tf", "M5"))
            distance *= tr.get("atr_multiplier", 2.0)
        else:
            distance = tr.get("distance", 0.0)
        if distance > 0:
            desired = round(market - distance if side == "BUY" else market + distance,
                            meta.get("digits", 2))
            improvement_ok = True
            if current_sl > 0:
                improvement = (desired - current_sl) if side == "BUY" else (current_sl - desired)
                improvement_ok = improvement >= (tr.get("step", 0.0) or 0.0)
            if _sl_would_tighten(side, desired, current_sl) and improvement_ok \
               and abs(desired - market) >= min_dist:
                result = _send_sltp(gw, mt5, pos, desired, current_tp)
                actions.append({"ticket": ticket, "action": f"trailing_{tr['mode']}",
                                "sl": desired, "ok": result["ok"]})

    # 5) Time exit (tempo maximo em minutos ou horario fixo)
    te = rule.get("time_exit")
    if te:
        close_now = False
        reason = ""
        opened_raw = st.get("opened_at")
        try:
            opened = datetime.fromisoformat(str(opened_raw)) if opened_raw else None
        except ValueError:
            opened = None
        minutes = _num(te.get("max_minutes"), 0.0)
        if minutes > 0 and opened and datetime.now() - opened >= timedelta(minutes=minutes):
            close_now = True
            reason = f"max_minutes={minutes:g}"
        close_at = str(te.get("close_at", "")).strip()
        if not close_now and close_at:
            try:
                hh, mm = close_at.split(":")[:2]
                now = datetime.now()
                target_dt = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                if target_dt < now - timedelta(minutes=1):
                    target_dt += timedelta(days=1)
                if now >= target_dt:
                    close_now = True
                    reason = f"close_at={close_at}"
            except (ValueError, IndexError):
                pass
        if close_now:
            if te.get("only_if_loss") and profit >= 0:
                return
        try:
            result = gw._demo_close({"ticket": ticket, "confirm_demo": True})
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
        intent_log.record_intent("guardian_time_exit",
                                 {"ticket": ticket, "reason": reason, "symbol": rule.get("symbol", "")},
                                 status="sent" if result.get("ok") else "failed",
                                 extra={"retcode": result.get("retcode"), "error": result.get("error")})
        actions.append({"ticket": ticket, "action": "time_exit", "reason": reason,
                        "ok": bool(result.get("ok"))})


def guardian_tick() -> dict:
    """Um ciclo do guardian sobre todas as regras ativas."""
    from backend import mt5_gateway as gw
    emergency = _emergency_stop()
    if emergency:
        _TICK_INFO.update({"last_tick": _now_iso(), "emergency_stop": True,
                           "actions": [{"action": "paused", "reason": "parada de emergencia ativa"}],
                           "error": None})
        return {"ok": True, "paused": "emergency_stop", "count": len(RULES)}
    with _LOCK:
        snapshot = {t: dict(r) for t, r in RULES.items()}
    if not snapshot:
        _TICK_INFO.update({"last_tick": _now_iso(), "actions": [], "error": None,
                           "emergency_stop": False})
        return {"ok": True, "count": 0}
    actions: list = []
    error = None
    try:
        mt5 = gw._mt5()
        for ticket, rule in snapshot.items():
            try:
                _guard_tick_rule(gw, mt5, ticket, rule, actions)
            except Exception as exc:  # falha em uma regra nao para as outras
                actions.append({"ticket": ticket, "action": "error", "error": str(exc)})
    except Exception as exc:
        error = str(exc)
    _TICK_INFO.update({"last_tick": _now_iso(), "actions": actions[-50:], "error": error,
                       "emergency_stop": False})
    if actions or error:
        _watchdog.record("guardian_tick", {"count": len(snapshot), "actions": actions[-10:],
                                           "error": error},
                         severity="warning" if error else "info")
    return {"ok": True, "count": len(snapshot), "actions": actions, "error": error}


def _loop() -> None:
    while True:
        try:
            guardian_tick()
        except Exception:
            pass
        time.sleep(max(0.2, INTERVAL_SEC))


def start_guardian_loop() -> None:
    """Sobe o daemon de ticks (idempotente) e carrega regras persistidas."""
    global _LOOP_STARTED
    with _LOCK:
        if _LOOP_STARTED:
            return
        _LOOP_STARTED = True
    _load_rules()
    threading.Thread(target=_loop, name="guardian-engine", daemon=True).start()
