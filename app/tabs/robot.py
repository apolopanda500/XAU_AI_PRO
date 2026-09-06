"""
Aba de controle do Robo MT5.
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, DangerButton, AccentButton
from app.config_manager import get_config
from app.learning_engine import get_learning_engine
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class RobotTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        from app.components.banner import TabBanner
        TabBanner(self.frame, "robot")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Controle do Robo MT5", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.header_state = tk.Label(header, text="EA: aguardando", bg=Theme.BG, fg=Theme.WARNING,
                                     font=(Theme.FONT_FAMILY, 10, "bold"))
        self.header_state.pack(side="right")

        self.status_card = Card(self.frame, title="Status do Robo")
        self.status_card.pack(fill="x", padx=24, pady=10)
        self.status_text = tk.Label(self.status_card.body, text="Desconectado", bg=Theme.CARD,
                                    fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 11),
                                    anchor="w", justify="left")
        self.status_text.pack(fill="x", padx=8, pady=8)
        self.health_row = tk.Frame(self.status_card.body, bg=Theme.CARD)
        self.health_row.pack(fill="x", padx=8, pady=(0, 8))
        self.health_labels = {}
        for key in ("Terminal", "EA", "Magic", "Predicoes"):
            box = tk.Frame(self.health_row, bg=Theme.CARD)
            box.pack(side="left", expand=True, fill="both", padx=6)
            tk.Label(box, text=key, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(anchor="w")
            lbl = tk.Label(box, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_FAMILY, 16, "bold"))
            lbl.pack(anchor="w", pady=(4, 0))
            self.health_labels[key] = lbl
        btn_row = tk.Frame(self.status_card.body, bg=Theme.CARD)
        btn_row.pack(fill="x", padx=8, pady=8)
        PrimaryButton(btn_row, text="Conectar MT5", command=self.connect, width=16).pack(side="left", padx=4)
        SecondaryButton(btn_row, text="Desconectar", command=self.disconnect, width=16).pack(side="left", padx=4)
        SecondaryButton(btn_row, text="Verificar EA", command=self.check_ea, width=16).pack(side="left", padx=4)

        action_card = Card(self.frame, title="Acoes Manuais")
        action_card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(action_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Simbolo", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=4)
        self.entry_symbol = tk.Entry(form, width=12, bg=Theme.PANEL, fg=Theme.TEXT,
                                     insertbackground=Theme.TEXT, relief="flat",
                                     highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_symbol.insert(0, get_config().get("trading", "default_symbol", default="XAUUSD"))
        self.entry_symbol.grid(row=0, column=1, padx=4)
        tk.Label(form, text="Lote", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=4)
        self.entry_volume = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                     insertbackground=Theme.TEXT, relief="flat",
                                     highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_volume.insert(0, "0.01")
        self.entry_volume.grid(row=0, column=3, padx=4)
        tk.Label(form, text="SL", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=4, padx=4)
        self.entry_sl = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                 insertbackground=Theme.TEXT, relief="flat",
                                 highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_sl.insert(0, "0")
        self.entry_sl.grid(row=0, column=5, padx=4)
        tk.Label(form, text="TP", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=6, padx=4)
        self.entry_tp = tk.Entry(form, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                 insertbackground=Theme.TEXT, relief="flat",
                                 highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_tp.insert(0, "0")
        self.entry_tp.grid(row=0, column=7, padx=4)
        AccentButton(form, text="Comprar", command=self.buy, width=10).grid(row=0, column=8, padx=4)
        DangerButton(form, text="Vender", command=self.sell, width=10).grid(row=0, column=9, padx=4)

        # ------------------------------------------------------------------
        # Painel de Risco e Execução PRO (estilo Trade Control MTS / EXP FOREX)
        # ------------------------------------------------------------------
        risk_card = Card(self.frame, title="Risco e Execucao PRO")
        risk_card.pack(fill="x", padx=24, pady=10)

        # Campos numéricos estilo terminal (Lot, SL/TP em pips, Risk%)
        rform = tk.Frame(risk_card.body, bg=Theme.CARD)
        rform.pack(fill="x", padx=8, pady=(8, 4))
        self.r_fields: dict[str, tuple[tk.Entry, tk.Label]] = {}
        r_specs = [
            ("Lote", "lot", "0.01"), ("Risk %", "risk", "4.0"),
            ("R/TP", "rtp", "2.0"), ("R/SL", "rsl", "1.0"),
            ("SL (p)", "slp", "50"), ("TP (p)", "tpp", "0"),
        ]
        for col, (label, key, default_value) in enumerate(r_specs):
            box = tk.Frame(rform, bg=Theme.CARD)
            box.pack(side="left", expand=True, fill="both", padx=3)
            tk.Label(box, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(anchor="w")
            entry = tk.Entry(box, width=8, bg=Theme.PANEL, fg=Theme.TEXT,
                             insertbackground=Theme.TEXT, relief="flat",
                             highlightbackground=Theme.BORDER, highlightthickness=1,
                             font=(Theme.FONT_MONO, 10))
            entry.insert(0, default_value)
            entry.pack(anchor="w", pady=(2, 0))
            self.r_fields[key] = (entry, box)

        # Métricas calculáveis (estáticas para visual INSTITUTIONAL)
        self.risk_metric = tk.Frame(risk_card.body, bg=Theme.CARD)
        self.risk_metric.pack(fill="x", padx=8, pady=(4, 8))
        self.risk_labels: dict[str, tk.Label] = {}
        for c, (key, label_text) in enumerate([
            ("drawdown", "Drawdown lim."), ("slv", "Risco/Stop"),
            ("tam", "Tamanho pos"), ("modo", "Modo")
        ]):
            box = tk.Frame(self.risk_metric, bg=Theme.CARD)
            box.pack(side="left", expand=True, fill="both", padx=3)
            tk.Label(box, text=label_text, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(anchor="w")
            lbl = tk.Label(box, text="--", bg=Theme.CARD, fg=Theme.PRIMARY,
                           font=(Theme.FONT_FAMILY, 13, "bold"))
            lbl.pack(anchor="w", pady=(2, 0))
            self.risk_labels[key] = lbl

        # Botões rápidos estilo terminal (STOP / MODIFY / Buy / Sell)
        ractions = tk.Frame(risk_card.body, bg=Theme.CARD)
        ractions.pack(fill="x", padx=8, pady=(0, 10))
        DangerButton(ractions, text="PARAR (STOP)", command=self.stop_trading, width=16).pack(side="left", padx=4)
        SecondaryButton(ractions, text="MODIFY only", command=self.modify_only, width=14).pack(side="left", padx=4)
        AccentButton(ractions, text="Comprar", command=self.buy, width=10).pack(side="left", padx=4)
        DangerButton(ractions, text="Vender", command=self.sell, width=10).pack(side="left", padx=4)
        SecondaryButton(ractions, text="Fechar ultima", command=self.close_last, width=14).pack(side="left", padx=4)
        self.risk_status = tk.Label(ractions, text="", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                    font=(Theme.FONT_FAMILY, 9))
        self.risk_status.pack(side="left", padx=10)

        self._apply_risk_defaults()

        ai_card = Card(self.frame, title="Aprendizado Continuo")
        ai_card.pack(fill="x", padx=24, pady=10)
        ai_row = tk.Frame(ai_card.body, bg=Theme.CARD)
        ai_row.pack(fill="x", padx=8, pady=8)
        PrimaryButton(ai_row, text="Treinar agora", command=self.train_now, width=16).pack(side="left", padx=4)
        SecondaryButton(ai_row, text="Sincronizar predicoes", command=self.sync_predictions, width=20).pack(side="left", padx=4)
        self.ai_status = tk.Label(ai_row, text="Parado", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                  font=(Theme.FONT_FAMILY, 10))
        self.ai_status.pack(side="left", padx=12)

    def connect(self) -> None:
        cfg_path = get_config().get("mt5", "terminal_path", default="")
        if self.robot.connect(path=cfg_path if cfg_path else None):
            self.on_status("MT5 conectado")
        else:
            self.on_status(f"Falha MT5: {self.robot.last_error}")
        self.check_ea()

    def disconnect(self) -> None:
        self.robot.disconnect()
        self.on_status("MT5 desconectado")
        self.check_ea()

    def check_ea(self) -> None:
        if not self.robot.connected:
            self.status_text.configure(text="Desconectado", fg=Theme.TEXT_MUTED)
            self.header_state.configure(text="EA: offline", fg=Theme.DANGER)
            self.health_labels["Terminal"].configure(text="OFF", fg=Theme.DANGER)
            self.health_labels["EA"].configure(text="OFF", fg=Theme.DANGER)
            self.health_labels["Magic"].configure(text="0", fg=Theme.TEXT_SECONDARY)
            self.health_labels["Predicoes"].configure(text="N/D", fg=Theme.TEXT_SECONDARY)
            return
        ea = self.robot.is_ea_active()
        lines = [
            f"Terminal: {'conectado' if ea.get('connected') else 'desconectado'}",
            f"Posicoes com magic: {ea.get('positions_with_magic', 0)}",
            f"Predicoes recentes: {'sim' if ea.get('predictions_recent') else 'nao'}",
            f"Motivo: {ea.get('reason')}",
        ]
        active = bool(ea.get("active"))
        self.header_state.configure(text="EA: ativo" if active else "EA: atencao",
                                    fg=Theme.SUCCESS if active else Theme.WARNING)
        self.health_labels["Terminal"].configure(
            text="ON" if ea.get("connected") else "OFF",
            fg=Theme.SUCCESS if ea.get("connected") else Theme.DANGER,
        )
        self.health_labels["EA"].configure(
            text="ATIVO" if active else "PARADO",
            fg=Theme.SUCCESS if active else Theme.WARNING,
        )
        self.health_labels["Magic"].configure(
            text=str(ea.get("positions_with_magic", 0)),
            fg=Theme.PRIMARY,
        )
        self.health_labels["Predicoes"].configure(
            text="RECENTES" if ea.get("predictions_recent") else "STALE",
            fg=Theme.SUCCESS if ea.get("predictions_recent") else Theme.WARNING,
        )
        self.status_text.configure(text="\n".join(lines),
                                   fg=Theme.SUCCESS if active else Theme.WARNING)

    # ------------------------------------------------------------------
    # Painel de Risco e Execucao PRO (métodos)
    # ------------------------------------------------------------------
    def _apply_risk_defaults(self) -> None:
        """Carrega defaults de risco da config e preenche campos/métricas."""
        cfg = get_config()
        risk_pct = cfg.get("risk", "RiskPercent", default=4.0) or 4.0
        try:
            if "lot" in self.r_fields:
                self.r_fields["lot"][0].delete(0, "end")
                self.r_fields["lot"][0].insert(0, str(cfg.get("trading", "default_volume", default=0.01)))
            if "risk" in self.r_fields:
                self.r_fields["risk"][0].delete(0, "end")
                self.r_fields["risk"][0].insert(0, str(risk_pct))
        except Exception:
            pass
        try:
            self.risk_labels["drawdown"].configure(text="--")
            self.risk_labels["slv"].configure(text="1 : 1")
            self.risk_labels["tam"].configure(text="--")
            self.risk_labels["modo"].configure(text="AUTO", fg=Theme.ACCENT)
        except Exception:
            pass

    def _recalc_risk(self) -> None:
        """Recalcula métricas visuais a partir dos campos (sem tocar risco real)."""
        try:
            lot = float(self._risk_field("lot") or 0)
            risk = float(self._risk_field("risk") or 0)
        except ValueError:
            return
        self.risk_labels["tam"].configure(text=f"{lot:.2f} @ {risk:.1f}%")
        self.risk_labels["modo"].configure(text="MANUAL" if lot else "AUTO", fg=Theme.PRIMARY)

    def _risk_field(self, key: str) -> str:
        try:
            return self.r_fields[key][0].get().strip()
        except Exception:
            return ""

    def stop_trading(self) -> None:
        """Registra o comando STOP (emergência). Exige confirmação para aplicar."""
        if not self.robot.connected:
            self.risk_status.configure(text="MT5 desconectado", fg=Theme.WARNING)
            self.on_status("STOP: MT5 desconectado")
            return
        confirm = messagebox.askyesno(
            "Parar trading (STOP)",
            "Registrar o comando STOP e fechar todas as posições abertas?",
        )
        if not confirm:
            self.risk_status.configure(text="Cancelado", fg=Theme.TEXT_MUTED)
            return
        try:
            res = self.robot.close_all_positions()
            if res.get("ok"):
                self.risk_status.configure(text="STOP aplicado", fg=Theme.DANGER)
                self.on_status("STOP: todas as posicoes fechadas")
                self._recalc_risk()
            else:
                self.risk_status.configure(text=f"Falha: {res.get('error')}", fg=Theme.DANGER)
        except Exception as e:
            self.risk_status.configure(text="Erro ao aplicar STOP", fg=Theme.DANGER)
            self.on_status(f"Erro STOP: {e}")

    def modify_only(self) -> None:
        """Ativa o modo 'MODIFY only' (sem novas entradas) no painel."""
        self.risk_labels["modo"].configure(text="MODIFY ONLY", fg=Theme.ACCENT)
        self.risk_status.configure(text="Modo modify-only ativo", fg=Theme.ACCENT)
        self.on_status("Modo MODIFY only ativado")

    def close_last(self) -> None:
        """Fecha a última posição aberta (após confirmação explícita)."""
        if not self.robot.connected:
            self.risk_status.configure(text="MT5 desconectado", fg=Theme.WARNING)
            self.on_status("Close last: MT5 desconectado")
            return
        positions = self.robot.get_positions()
        if not positions:
            self.risk_status.configure(text="Sem posicoes abertas", fg=Theme.TEXT_MUTED)
            return
        last = positions[-1]
        ticket = getattr(last, "ticket", None)
        if ticket is None and isinstance(last, dict):
            ticket = last.get("ticket")
        confirm = messagebox.askyesno(
            "Fechar ultima posicao", f"Deseja fechar a posicao ticket={ticket}?"
        )
        if not confirm:
            self.risk_status.configure(text="Cancelado", fg=Theme.TEXT_MUTED)
            return
        try:
            res = self.robot.close_position(ticket)
            if res.get("ok"):
                self.risk_status.configure(text="Ultima posicao fechada", fg=Theme.SUCCESS)
                self.on_status(f"Posicao {ticket} fechada")
                self._recalc_risk()
            else:
                self.risk_status.configure(text=f"Falha: {res.get('error')}", fg=Theme.DANGER)
        except Exception as e:
            self.risk_status.configure(text="Erro ao fechar", fg=Theme.DANGER)
            self.on_status(f"Erro close: {e}")

    def buy(self) -> None:
        self._send("BUY")

    def sell(self) -> None:
        self._send("SELL")

    def _send(self, side: str) -> None:
        symbol = self.entry_symbol.get().strip()
        try:
            volume = float(self.entry_volume.get())
            sl = float(self.entry_sl.get())
            tp = float(self.entry_tp.get())
        except ValueError:
            self.on_status("Valores invalidos")
            return
        if not self.robot.connected:
            self.on_status("Ordem nao enviada: MT5 desconectado")
            return
        account = self.robot.account_info()
        if not account or not account.get("trade_allowed"):
            self.on_status("Ordem nao enviada: negociacao nao autorizada no terminal")
            return
        action = "COMPRA" if side == "BUY" else "VENDA"
        details = f"{action} REAL\nAtivo: {symbol}\nVolume: {volume}\nSL: {sl or 'nao definido'}\nTP: {tp or 'nao definido'}"
        if not messagebox.askyesno("Confirmar ordem real", details):
            return
        res = self.robot.send_order(symbol, side, volume, sl=sl, tp=tp)
        if res.get("ok"):
            self.on_status(f"Ordem {side} {symbol} enviada, ticket {res['ticket']}")
        else:
            self.on_status(f"Erro ordem: {res.get('error')}")

    def train_now(self) -> None:
        self.ai_status.configure(text="Treinando...", fg=Theme.WARNING)
        self.on_status("Iniciando treinamento...")
        def run():
            result = get_learning_engine().full_cycle()
            self.ai_status.configure(text="Concluido" if result.get("ok") else "Erro",
                                     fg=Theme.SUCCESS if result.get("ok") else Theme.DANGER)
            self.on_status(result.get("predict", {}).get("sync", {}).get("error", "Treinamento finalizado"))
        threading.Thread(target=run, daemon=True).start()

    def sync_predictions(self) -> None:
        res = self.robot.sync_predictions()
        if res.get("ok"):
            self.on_status(f"{res.get('copied', 0)} predicoes sincronizadas")
        else:
            self.on_status(f"Erro sync: {res.get('error')}")
