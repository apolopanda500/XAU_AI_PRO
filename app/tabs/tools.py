"""
Aba Ferramentas do app XAU_AI_PRO.

Painel de ferramentas e monitoramento:
  - Historico de Operacoes (full_audit.csv do EA + historico MT5)
  - Movimentos do Robo (log do terminal / journal em tempo real)
  - Estatisticas de performance (win rate, P/L, por simbolo)
  - Calculadora de lote e Notas diarias
Auto-refresh: a cada 1 min (nao trava a GUI - coleta em thread daemon).
"""
from __future__ import annotations

import csv
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.components.tables import HistoryTable
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme
from app.utils.async_ui import run_bg

# Caminho do audit do EA (gerado pelo MQL5) - busca em varias localizacoes
_RES = Path(__file__).resolve()
# _RES parents: [0]=tabs [1]=app [2]=XAU_AI_PRO [3]=Files [4]=MQL5 [5]=TerminalID
_AUDIT_CANDIDATES = [
    _RES.parents[4] / "Files" / "Data" / "full_audit.csv",   # MQL5\Files\Data (terminal)
    _RES.parents[2] / "MQL5" / "Files" / "Data" / "full_audit.csv",  # dentro do projeto
    _RES.parents[2] / "Files" / "Data" / "full_audit.csv",   # variacao
]
_LOGS_DIR = _RES.parents[5] / "Logs" if len(_RES.parents) > 5 else _RES.parents[4].parent / "Logs"


def _find_audit() -> Path | None:
    for p in _AUDIT_CANDIDATES:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    # fallback: rastreia no Files/Data
    try:
        data_root = _RES.parents[4] / "Files" / "Data"
        if data_root.exists():
            for pp in data_root.glob("**/full_audit.csv"):
                return pp
    except Exception:
        pass
    return None


def _current_log_path() -> Path | None:
    """Log do terminal atual (Logs/YYYYMMDD.log) ou o mais recente."""
    today = datetime.now().strftime("%Y%m%d")
    p = _LOGS_DIR / f"{today}.log"
    if p.exists():
        return p
    # fallback: mais recente
    try:
        logs = sorted(_LOGS_DIR.glob("*.log"))
        return logs[-1] if logs else None
    except Exception:
        return None


class ToolsTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._auto_running = False
        self._build()

    def _build(self) -> None:
        from app.components.banner import TabBanner
        TabBanner(self.frame, "tools")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Auditoria e Ferramentas", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Historico operacional, journal e utilitarios do trader",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)
        self.last_lbl = tk.Label(header, text="Atualizado: --", bg=Theme.BG,
                                 fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9))
        self.last_lbl.pack(side="right")
        PrimaryButton(header, text="Atualizar", command=self.refresh, width=12).pack(side="right", padx=8)

        # ---------------- Historico de Operacoes ----------------
        hist_card = Card(self.frame, title="Historico de Operacoes (EA + MT5)")
        hist_card.pack(fill="x", padx=24, pady=10)
        stats_row = tk.Frame(hist_card.body, bg=Theme.CARD)
        stats_row.pack(fill="x", padx=8, pady=(8, 4))
        self.lbl_total = tk.Label(stats_row, text="Total: --", bg=Theme.CARD, fg=Theme.TEXT,
                                  font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_total.pack(side="left", padx=8)
        self.lbl_wins = tk.Label(stats_row, text="Wins: --", bg=Theme.CARD, fg=Theme.SUCCESS,
                                 font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_wins.pack(side="left", padx=8)
        self.lbl_losses = tk.Label(stats_row, text="Losses: --", bg=Theme.CARD, fg=Theme.DANGER,
                                   font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_losses.pack(side="left", padx=8)
        self.lbl_winrate = tk.Label(stats_row, text="WinRate: --", bg=Theme.CARD, fg=Theme.PRIMARY,
                                    font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_winrate.pack(side="left", padx=8)
        self.lbl_pnl = tk.Label(stats_row, text="P/L: --", bg=Theme.CARD, fg=Theme.TEXT,
                                font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_pnl.pack(side="left", padx=8)
        self.lbl_source = tk.Label(stats_row, text="", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                                   font=(Theme.FONT_FAMILY, 8))
        self.lbl_source.pack(side="right", padx=8)
        self.hist_table = HistoryTable(hist_card.body)
        self.hist_table.pack(fill="x", padx=8, pady=8)

        # ---------------- Movimentos do Robo ----------------
        mov_card = Card(self.frame, title="Movimentos do Robo (journal do terminal)")
        mov_card.pack(fill="both", expand=True, padx=24, pady=10)
        self.mov_text = tk.Text(mov_card.body, bg=Theme.PANEL, fg=Theme.TEXT,
                                font=("Consolas", 9), relief="flat", wrap="none",
                                height=10, state="disabled")
        self.mov_text.pack(fill="both", expand=True, padx=8, pady=8)
        mov_row = tk.Frame(mov_card.body, bg=Theme.CARD)
        mov_row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(mov_row, text="Filtro", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        self.mov_filter = tk.Entry(mov_row, width=24, bg=Theme.PANEL, fg=Theme.TEXT, relief="flat",
                                   highlightbackground=Theme.BORDER, highlightthickness=1)
        self.mov_filter.insert(0, "Trades")
        self.mov_filter.pack(side="left", padx=4)
        SecondaryButton(mov_row, text="Aplicar", command=self.refresh_movimentos, width=10).pack(side="left", padx=6)

        # ---------------- Calculadora de Lote + Notas ----------------
        bottom = tk.Frame(self.frame, bg=Theme.BG)
        bottom.pack(fill="x", padx=24, pady=10)
        lot_card = Card(bottom, title="Calculadora de Lote")
        lot_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        form = tk.Frame(lot_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Saldo", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=4, pady=4)
        self.entry_balance = tk.Entry(form, width=12, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                      relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_balance.grid(row=0, column=1, padx=4)
        tk.Label(form, text="Risco %", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=4)
        self.entry_risk = tk.Entry(form, width=8, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                   relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_risk.insert(0, "1.0")
        self.entry_risk.grid(row=0, column=3, padx=4)
        tk.Label(form, text="SL pts", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=4, padx=4)
        self.entry_sl_points = tk.Entry(form, width=8, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                        relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_sl_points.insert(0, "300")
        self.entry_sl_points.grid(row=0, column=5, padx=4)
        tk.Label(form, text="Ponto ($)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=6, padx=4)
        self.entry_point = tk.Entry(form, width=8, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_point.insert(0, "0.01")
        self.entry_point.grid(row=0, column=7, padx=4)
        AccentButton(form, text="Calcular", command=self.calc_lot, width=10).grid(row=0, column=8, padx=8)
        self.lot_result = tk.Label(form, text="Lote = --", bg=Theme.CARD, fg=Theme.PRIMARY,
                                   font=(Theme.FONT_FAMILY, 11, "bold"))
        self.lot_result.grid(row=1, column=0, columnspan=9, pady=8)

        notes_card = Card(bottom, title="Notas Diarias")
        notes_card.pack(side="left", fill="both", expand=True)
        self.notes = tk.Text(notes_card.body, bg=Theme.PANEL, fg=Theme.TEXT, font=(Theme.FONT_FAMILY, 10),
                             relief="flat", wrap="word", height=6)
        self.notes.pack(fill="both", expand=True, padx=8, pady=8)
        SecondaryButton(notes_card.body, text="Salvar notas", command=self.save_notes, width=14).pack(anchor="e", padx=8, pady=8)
        self._load_notes()

    # ------------------------------------------------------------------
    # Auto-refresh (1 min)
    # ------------------------------------------------------------------
    def start_auto_refresh(self, interval_sec: int = 60) -> None:
        self._auto_running = True

        def loop() -> None:
            while self._auto_running:
                try:
                    interval = max(30, interval_sec)
                    time.sleep(interval)
                    if self._auto_running:
                        self.refresh()
                except Exception:
                    time.sleep(10)

        threading.Thread(target=loop, daemon=True).start()

    def stop_auto_refresh(self) -> None:
        self._auto_running = False

    # ------------------------------------------------------------------
    # Refresh geral
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        run_bg(
            self.frame,
            work=self._collect,
            apply_result=self._apply,
        )

    def _collect(self) -> dict[str, Any]:
        out: dict[str, Any] = {"ts": datetime.now().strftime("%H:%M:%S"),
                               "audit": [], "moves": [], "mt5_deals": []}
        # 1) full_audit.csv do EA
        out["audit"] = self._read_audit()
        # 2) movimentos do robô (journal)
        out["moves"] = self._read_movimentos()
        # 3) historico MT5
        try:
            out["mt5_deals"] = self.robot.get_history(days=30)
        except Exception:
            out["mt5_deals"] = []
        return out

    def _apply(self, data: dict[str, Any]) -> None:
        # Historico: combina audit (EA) com deals MT5
        audit = data.get("audit") or []
        deals = data.get("mt5_deals") or []
        self._apply_stats(audit, deals)
        self._apply_history(audit, deals)
        self._apply_movimentos(data.get("moves") or [])
        self.last_lbl.configure(text=f"Atualizado: {data.get('ts', '')}")

    # ------------------------------------------------------------------
    # Historico + estatisticas
    # ------------------------------------------------------------------
    def _read_audit(self, limit: int = 100) -> list[dict[str, str]]:
        """Le o full_audit.csv do EA (ponto-e-virgula, varios encodings)."""
        path = _find_audit()
        if not path:
            return []
        rows: list[dict[str, str]] = []
        try:
            for enc in ("utf-8-sig", "utf-16-le", "cp1252"):
                try:
                    with open(path, encoding=enc, errors="ignore") as fh:
                        reader = csv.DictReader(fh, delimiter=";")
                        data = [r for r in reader if r.get("Ticket")]
                    if data:
                        rows = data
                        break
                except Exception:
                    continue
        except Exception:
            return []
        # filtra linhas com Result (fechamentos) e sem (entradas)
        return rows[-limit:]

    def _apply_stats(self, audit: list[dict], deals: list[Any]) -> None:
        # wins/losses a partir do Result do audit (strings numericas)
        wins = 0
        losses = 0
        neutral = 0
        pnl = 0.0
        total = len(audit)
        if audit:
            for r in audit:
                res = (r.get("Result") or "").strip().replace(",", ".")
                try:
                    v = float(res) if res else 0.0
                    if v > 0:
                        wins += 1
                    elif v < 0:
                        losses += 1
                    else:
                        neutral += 1
                    pnl += v
                except ValueError:
                    pass
        elif deals:
            total = len(deals)
            pnl = sum(d.profit for d in deals)
            wins = sum(1 for d in deals if d.profit > 0)
            losses = sum(1 for d in deals if d.profit < 0)

        self.lbl_total.configure(text=f"Total: {total}")
        self.lbl_wins.configure(text=f"Wins: {wins}")
        self.lbl_losses.configure(text=f"Losses: {losses}")
        decided = wins + losses
        wr = (wins / decided * 100) if decided else 0
        self.lbl_winrate.configure(text=f"WinRate: {wr:.1f}%")
        self.lbl_pnl.configure(text=f"P/L: {pnl:.2f}",
                               fg=Theme.SUCCESS if pnl >= 0 else Theme.DANGER)
        self.lbl_source.configure(text="fonte: full_audit.csv (EA)" if audit else
                                  ("fonte: MT5 30d" if deals else "sem dados"))

    def _apply_history(self, audit: list[dict], deals: list[Any]) -> None:
        rows: list[list[str]] = []
        tags: list[str] = []
        # prioriza audit do EA (detalhado)
        for r in audit:
            res = (r.get("Result") or "").strip()
            try:
                res_f = float(res.replace(",", ".")) if res else 0.0
            except ValueError:
                res_f = None
            rows.append([
                r.get("Time", ""), r.get("Ticket", ""), r.get("Symbol", ""),
                r.get("Price", ""), r.get("AI_Signal", "") or r.get("Side", ""),
                r.get("AI_Confidence", ""), r.get("Entry_Reason", ""),
                r.get("Exit_Reason", "") or "", res,
            ])
            tags.append("profit" if (res_f or 0) > 0 else ("loss" if (res_f or 0) < 0 else "flat"))
        if not rows and deals:
            for d in deals:
                rows.append([
                    d.time, str(d.ticket), d.symbol, f"{d.price:.5f}",
                    d.type, "", "", "", f"{d.profit:.2f}",
                ])
                tags.append("profit" if d.profit >= 0 else "loss")
        if not rows:
            rows = [["--"] * 9]
            tags = ["flat"]
        self.hist_table.tree.set_rows(rows, tags)

    # ------------------------------------------------------------------
    # Movimentos do robo (journal)
    # ------------------------------------------------------------------
    def _read_movimentos(self, limit: int = 40) -> list[str]:
        logp = _current_log_path()
        if not logp:
            return ["Sem log de terminal disponivel"]
        filtro = self.mov_filter.get().strip() or "Trades"
        try:
            raw = logp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            try:
                raw = logp.read_text(encoding="cp1252", errors="ignore")
            except Exception:
                return ["Nao foi possivel ler o log"]
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        # linhas da conta atual + filtro
        acct = ""
        try:
            info = self.robot.account_info()
            acct = str(info.get("login", "")) if info else ""
        except Exception:
            pass
        sel = []
        for ln in lines:
            if filtro.lower() not in ln.lower():
                continue
            if acct and ("'" + acct + "'" in ln or acct in ln):
                pass
            if "XAU_AI_PRO" in ln or "Trades" in ln or "orders" in ln.lower() or "deal" in ln.lower() or "expert" in ln.lower():
                sel.append(ln)
        if not sel:
            sel = [ln for ln in lines if filtro.lower() in ln.lower()][-limit:]
        return sel[-limit:]

    def refresh_movimentos(self) -> None:
        moves = self._read_movimentos()
        self._apply_movimentos(moves)

    def _apply_movimentos(self, moves: list[str]) -> None:
        self.mov_text.configure(state="normal")
        self.mov_text.delete("1.0", "end")
        if not moves:
            self.mov_text.insert("1.0", "Nenhum movimento encontrado (ajuste o filtro).")
        else:
            self.mov_text.insert("1.0", "\n".join(moves))
        self.mov_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def calc_lot(self) -> None:
        try:
            balance = float(self.entry_balance.get())
            risk = float(self.entry_risk.get()) / 100.0
            sl_points = float(self.entry_sl_points.get())
            point_value = float(self.entry_point.get())
            if sl_points <= 0 or point_value <= 0 or balance <= 0:
                raise ValueError
            risk_amount = balance * risk
            lot = risk_amount / (sl_points * point_value)
            self.lot_result.configure(text=f"Lote = {lot:.2f}")
            self.on_status(f"Lote calculado: {lot:.2f}")
        except ValueError:
            self.lot_result.configure(text="Lote = valores invalidos")

    def _notes_path(self) -> Path:
        root = Path(__file__).resolve().parent.parent
        p = root / "data" / "notes.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def _load_notes(self) -> None:
        try:
            p = self._notes_path()
            if p.exists():
                self.notes.insert("1.0", p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass

    def save_notes(self) -> None:
        text = self.notes.get("1.0", "end")
        try:
            self._notes_path().write_text(text, encoding="utf-8")
            self.on_status(f"Notas salvas ({len(text)} caracteres)")
        except Exception as e:
            self.on_status(f"Erro ao salvar notas: {e}")
