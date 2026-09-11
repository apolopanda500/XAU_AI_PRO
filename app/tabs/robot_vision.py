# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Robot Vision - mostra como o robo enxerga o mercado.

Exibe:
- Indicadores que o EA esta usando em tempo real
- Sinais de entrada/saida
- Analise de risco atual
- Heatmap de forca de sinais
- Comparacao com operacoes passadas
"""
from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.data.indicators import calculate
from app.theme.mexc import Theme


class RobotVision(tk.Frame):
    """Painel de visualizacao da 'mente' do robo."""

    def __init__(self, parent, robot, market, on_status: Callable):
        super().__init__(parent, bg=Theme.BG)
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = self
        self._running = False
        self._candles: list[dict] = []
        self._vision_data: dict = {}
        self._build()
        self._start_refresh()

    def _build(self):
        from app.components.banner import TabBanner
        TabBanner(self.frame, "robot")

        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Visao do Robo", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.status_label = tk.Label(header, text="Analisando...", bg=Theme.BG, fg=Theme.WARNING,
                                      font=(Theme.FONT_FAMILY, 10))
        self.status_label.pack(side="right")

        main = tk.Frame(self.frame, bg=Theme.BG)
        main.pack(fill="both", expand=True, padx=24, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        # Indicadores em tempo real
        self._build_indicators_card(main, 0, 0)
        # Sinal atual
        self._build_signal_card(main, 0, 1)
        # Heatmap de forca
        self._build_heatmap_card(main, 1, 0)
        # Analise de risco
        self._build_risk_card(main, 1, 1)

    def _build_indicators_card(self, parent, row, col):
        card = Card(parent, title="Indicadores em Tempo Real", padx=12, pady=12)
        card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        self.ind_labels = {}
        for key in ["RSI(14)", "MACD(12,26,9)", "ATR(14)", "BB(20,2)", "Stoch(14,3)", "ADX(14)"]:
            row_f = tk.Frame(card.body, bg=Theme.CARD)
            row_f.pack(fill="x", pady=2)
            tk.Label(row_f, text=key + ":", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            lbl = tk.Label(row_f, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                          font=(Theme.FONT_FAMILY, 9, "bold"))
            lbl.pack(side="right")
            self.ind_labels[key] = lbl

    def _build_signal_card(self, parent, row, col):
        card = Card(parent, title="Sinal Atual", padx=12, pady=12)
        card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        self.signal_main = tk.Label(card.body, text="AGUARDANDO", bg=Theme.CARD,
                                     fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 24, "bold"))
        self.signal_main.pack(pady=12)
        self.signal_detail = tk.Label(card.body, text="Carregando dados...", bg=Theme.CARD,
                                       fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 10),
                                       wraplength=250, justify="center")
        self.signal_detail.pack(pady=8)

    def _build_heatmap_card(self, parent, row, col):
        card = Card(parent, title="Forca dos Indicadores", padx=12, pady=12)
        card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        self.heatmap_canvas = tk.Canvas(card.body, bg=Theme.BG, highlightthickness=0, height=150)
        self.heatmap_canvas.pack(fill="both", expand=True)

    def _build_risk_card(self, parent, row, col):
        card = Card(parent, title="Analise de Risco", padx=12, pady=12)
        card.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
        self.risk_labels = {}
        for key in ["Tendencia", "Volatilidade", "Forca do Sinal", "Risco/Beneficio", "Recomendacao"]:
            row_f = tk.Frame(card.body, bg=Theme.CARD)
            row_f.pack(fill="x", pady=3)
            tk.Label(row_f, text=key + ":", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            lbl = tk.Label(row_f, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                          font=(Theme.FONT_FAMILY, 9, "bold"))
            lbl.pack(side="right")
            self.risk_labels[key] = lbl

    def _start_refresh(self):
        """Inicia atualizacao periodica."""
        if self._running:
            return
        self._running = True
        self._refresh()

    def _refresh(self):
        """Atualiza dados periodicamente."""
        if not self._running:
            return
        threading.Thread(target=self._analyze_thread, daemon=True).start()
        self.frame.after(5000, self._refresh)  # atualiza a cada 5 segundos

    def _analyze_thread(self):
        """Analisa o mercado como o robo veria."""
        try:
            from app.mt5_lock import mt5_lock
            import MetaTrader5 as mt5
            symbol = "XAUUSD"
            with mt5_lock:
                mt5.symbol_select(symbol, True)
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
            if rates is not None and len(rates) >= 30:
                candles = []
                for r in rates:
                    candles.append({
                        "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]),
                        "volume": float(r["tick_volume"]),
                    })
                closes = [c["close"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                volumes = [c["volume"] for c in candles]
                # Calcular indicadores
                rsi = calculate("rsi", closes, highs, lows, volumes)["line"]
                macd = calculate("macd", closes, highs, lows, volumes)
                atr = calculate("atr", closes, highs, lows, volumes)["line"]
                bb = calculate("bb", closes, highs, lows, volumes)
                stoch = calculate("stoch", closes, highs, lows, volumes)
                adx = calculate("dmi", closes, highs, lows, volumes)
                self._vision_data = {
                    "rsi": rsi[-1] if rsi else 50,
                    "macd_hist": macd["histogram"][-1] if macd["histogram"] else 0,
                    "atr": atr[-1] if atr else 0,
                    "bb_pos": (closes[-1] - bb["lower"][-1]) / (bb["upper"][-1] - bb["lower"][-1]) if bb["upper"][-1] != bb["lower"][-1] else 0.5,
                    "stoch_k": stoch["k"][-1] if stoch["k"] else 50,
                    "adx": adx["adx"][-1] if adx["adx"] else 0,
                    "plus_di": adx["plus_di"][-1] if adx["plus_di"] else 0,
                    "minus_di": adx["minus_di"][-1] if adx["minus_di"] else 0,
                    "closes": closes,
                    "highs": highs,
                    "lows": lows,
                }
                self.frame.after(0, self._update_ui)
        except Exception as e:
            self.frame.after(0, lambda e=e: self.on_status(f"Robot Vision erro: {e}"))

    def _update_ui(self):
        """Atualiza a interface com os dados analisados."""
        d = self._vision_data
        if not d:
            return
        # Indicadores
        self.ind_labels["RSI(14)"].configure(text=f"{d['rsi']:.1f}")
        self.ind_labels["MACD(12,26,9)"].configure(text=f"{d['macd_hist']:.4f}")
        self.ind_labels["ATR(14)"].configure(text=f"{d['atr']:.2f}")
        self.ind_labels["BB(20,2)"].configure(text=f"{d['bb_pos']:.2%}")
        self.ind_labels["Stoch(14,3)"].configure(text=f"{d['stoch_k']:.1f}")
        self.ind_labels["ADX(14)"].configure(text=f"{d['adx']:.1f}")
        # Sinal
        signal, color, detail = self._determine_signal(d)
        self.signal_main.configure(text=signal, fg=color)
        self.signal_detail.configure(text=detail)
        # Risco
        self._update_risk(d)
        # Heatmap
        self._draw_heatmap(d)
        self.status_label.configure(text=f"Atualizado {datetime.now().strftime('%H:%M:%S')}", fg=Theme.SUCCESS)

    def _determine_signal(self, d):
        """Determina o sinal baseado nos indicadores."""
        score = 0
        reasons = []
        if d["rsi"] < 30:
            score += 2
            reasons.append("RSI sobrevendido")
        elif d["rsi"] > 70:
            score -= 2
            reasons.append("RSI sobrecomprado")
        if d["macd_hist"] > 0:
            score += 1
            reasons.append("MACD bullish")
        else:
            score -= 1
            reasons.append("MACD bearish")
        if d["plus_di"] > d["minus_di"]:
            score += 1
            reasons.append("+DI > -DI")
        else:
            score -= 1
            reasons.append("-DI > +DI")
        if d["stoch_k"] < 20:
            score += 1
            reasons.append("Stoch sobrevendido")
        elif d["stoch_k"] > 80:
            score -= 1
            reasons.append("Stoch sobrecomprado")
        if score >= 3:
            return "COMPRA FORTE", Theme.BID, " | ".join(reasons) if reasons else "Multiplos sinais de compra"
        elif score >= 1:
            return "COMPRA", Theme.SUCCESS, " | ".join(reasons) if reasons else "Sinais de compra"
        elif score <= -3:
            return "VENDA FORTE", Theme.ASK, " | ".join(reasons) if reasons else "Multiplos sinais de venda"
        elif score <= -1:
            return "VENDA", Theme.DANGER, " | ".join(reasons) if reasons else "Sinais de venda"
        else:
            return "NEUTRO", Theme.TEXT_MUTED, "Sem definicao clara"

    def _update_risk(self, d):
        """Atualiza analise de risco."""
        # Tendencia
        if d["adx"] > 25:
            trend = "Alta" if d["plus_di"] > d["minus_di"] else "Baixa"
            self.risk_labels["Tendencia"].configure(text=f"Forte {trend}", fg=Theme.WARNING)
        else:
            self.risk_labels["Tendencia"].configure(text="Lateral", fg=Theme.TEXT_MUTED)
        # Volatilidade
        if d["atr"] > 20:
            self.risk_labels["Volatilidade"].configure(text="Alta", fg=Theme.DANGER)
        elif d["atr"] > 10:
            self.risk_labels["Volatilidade"].configure(text="Media", fg=Theme.WARNING)
        else:
            self.risk_labels["Volatilidade"].configure(text="Baixa", fg=Theme.SUCCESS)
        # Forca do sinal
        if d["adx"] > 40:
            self.risk_labels["Forca do Sinal"].configure(text="Muito Forte", fg=Theme.BID)
        elif d["adx"] > 25:
            self.risk_labels["Forca do Sinal"].configure(text="Forte", fg=Theme.SUCCESS)
        else:
            self.risk_labels["Forca do Sinal"].configure(text="Fraco", fg=Theme.TEXT_MUTED)
        # Risco/Beneficio
        self.risk_labels["Risco/Beneficio"].configure(text="1:2 (estimado)")
        # Recomendacao
        if d["bb_pos"] > 0.9:
            self.risk_labels["Recomendacao"].configure(text="Sobrecuidado - Cuidado", fg=Theme.WARNING)
        elif d["bb_pos"] < 0.1:
            self.risk_labels["Recomendacao"].configure(text="Sobrevendido - Oportunidade", fg=Theme.SUCCESS)
        else:
            self.risk_labels["Recomendacao"].configure(text="Dentro da faixa normal", fg=Theme.TEXT)

    def _draw_heatmap(self, d):
        """Desenha heatmap de forca dos indicadores."""
        canvas = self.heatmap_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 10:
            return
        indicators = [
            ("RSI", d["rsi"] / 100),
            ("Stoch", d["stoch_k"] / 100),
            ("BB", d["bb_pos"]),
            ("ADX", min(d["adx"] / 50, 1)),
        ]
        bar_h = h / len(indicators)
        for i, (name, val) in enumerate(indicators):
            y = i * bar_h
            # Background
            canvas.create_rectangle(60, y + 2, w - 10, y + bar_h - 2, fill=Theme.PANEL, outline=Theme.BORDER)
            # Bar
            bar_w = max(2, (w - 80) * val)
            color = Theme.BID if val > 0.5 else Theme.ASK
            canvas.create_rectangle(60, y + 2, 60 + bar_w, y + bar_h - 2, fill=color, outline="")
            # Label
            canvas.create_text(5, y + bar_h / 2, text=name, fill=Theme.TEXT_SECONDARY,
                             font=(Theme.FONT_FAMILY, 8), anchor="w")
            canvas.create_text(w - 5, y + bar_h / 2, text=f"{val:.0%}", fill=Theme.TEXT,
                             font=(Theme.FONT_FAMILY, 8, "bold"), anchor="e")

    def stop(self):
        """Para a atualizacao periodica."""
        self._running = False
