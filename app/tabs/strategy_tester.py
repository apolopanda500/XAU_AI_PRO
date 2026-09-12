# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""Strategy Tester - validacao visual do robo no gráfico.

Permite:
- Backtesting com dados historicos do MT5
- Visualizar sinais de compra/venda no gráfico
- Configurar parametros dos indicadores
- Ver como o robo enxerga o mercado (Robot Vision)
- Simular operacoes com diferentes configuracoes
"""
from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.data.indicators import calculate, ALL_INDICATORS
from app.theme.mexc import Theme


class StrategyTester(tk.Frame):
    """Painel de Strategy Tester com backtesting e visualizacao de sinais."""

    def __init__(self, parent, on_status: Callable):
        super().__init__(parent, bg=Theme.BG)
        self.on_status = on_status
        self.frame = self
        self._running = False
        self._candles: list[dict] = []
        self._signals: list[dict] = []
        self._indicators: dict = {}
        self._build()

    def _build(self):
        from app.components.banner import TabBanner
        TabBanner(self.frame, "tools")

        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Strategy Tester", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.status_label = tk.Label(header, text="Pronto", bg=Theme.BG, fg=Theme.TEXT_MUTED,
                                      font=(Theme.FONT_FAMILY, 10))
        self.status_label.pack(side="right")

        # Layout principal: controles | grafico | resultados
        main = tk.Frame(self.frame, bg=Theme.BG)
        main.pack(fill="both", expand=True, padx=24, pady=10)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Painel esquerdo: controles
        self._build_controls(main, 0, 0)
        # Centro: grafico com sinais
        self._build_chart(main, 0, 1)
        # Direito: resultados
        self._build_results(main, 0, 2)

    def _build_controls(self, parent, row, col):
        panel = tk.Frame(parent, bg=Theme.BG_SECONDARY, width=280)
        panel.grid(row=row, column=col, sticky="ns", padx=(0, 8))
        panel.pack_propagate(False)

        # Simbolo
        sym_card = Card(panel, title="Ativo", padx=12, pady=12)
        sym_card.pack(fill="x", padx=8, pady=8)
        self.sym_var = tk.StringVar(value="XAUUSD")
        tk.Entry(sym_card.body, textvariable=self.sym_var, bg=Theme.PANEL, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 11), relief="flat").pack(fill="x", pady=4)

        # Timeframe
        tf_card = Card(panel, title="Timeframe", padx=12, pady=12)
        tf_card.pack(fill="x", padx=8, pady=4)
        self.tf_var = tk.StringVar(value="H1")
        for tf in ["M5", "M15", "M30", "H1", "H4", "D1"]:
            tk.Radiobutton(tf_card.body, text=tf, variable=self.tf_var, value=tf,
                          bg=Theme.CARD, fg=Theme.TEXT, selectcolor=Theme.PRIMARY,
                          font=(Theme.FONT_FAMILY, 9)).pack(side="left", padx=2)

        # Indicadores
        ind_card = Card(panel, title="Indicadores", padx=12, pady=12)
        ind_card.pack(fill="x", padx=8, pady=4)
        self.ind_vars = {}
        for key in ["macd", "rsi", "bb", "stoch", "atr", "ichimoku"]:
            var = tk.BooleanVar(value=key in ("macd", "rsi", "bb"))
            self.ind_vars[key] = var
            tk.Checkbutton(ind_card.body, text=ALL_INDICATORS[key]["name"],
                          variable=var, bg=Theme.CARD, fg=Theme.TEXT,
                          selectcolor=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9),
                          anchor="w").pack(fill="x", pady=1)

        # Botoes
        btn_card = Card(panel, title="Acoes", padx=12, pady=12)
        btn_card.pack(fill="x", padx=8, pady=4)
        PrimaryButton(btn_card.body, text="Carregar Dados", command=self._load_data).pack(fill="x", pady=2)
        AccentButton(btn_card.body, text="Gerar Sinais", command=self._generate_signals).pack(fill="x", pady=2)
        SecondaryButton(btn_card.body, text="Limpar", command=self._clear).pack(fill="x", pady=2)

    def _build_chart(self, parent, row, col):
        chart_card = Card(parent, title="Grafico com Sinais", padx=8, pady=8)
        chart_card.grid(row=row, column=col, sticky="nsew", padx=4)

        self.chart_canvas = tk.Canvas(chart_card.body, bg=Theme.BG, highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", lambda e: self._draw_chart())

    def _build_results(self, parent, row, col):
        panel = tk.Frame(parent, bg=Theme.BG_SECONDARY, width=250)
        panel.grid(row=row, column=col, sticky="ns", padx=(8, 0))
        panel.pack_propagate(False)

        # Estatisticas
        stats_card = Card(panel, title="Estatisticas", padx=12, pady=12)
        stats_card.pack(fill="x", padx=8, pady=8)
        self.stats_labels = {}
        for key in ["Total Sinais", "Compras", "Vendas", "Win Rate", "Profit"]:
            row_f = tk.Frame(stats_card.body, bg=Theme.CARD)
            row_f.pack(fill="x", pady=2)
            tk.Label(row_f, text=key + ":", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).pack(side="left")
            lbl = tk.Label(row_f, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                          font=(Theme.FONT_FAMILY, 9, "bold"))
            lbl.pack(side="right")
            self.stats_labels[key] = lbl

        # Lista de sinais
        sig_card = Card(panel, title="Sinais", padx=12, pady=12)
        sig_card.pack(fill="both", expand=True, padx=8, pady=4)
        self.signals_list = tk.Text(sig_card.body, bg=Theme.PANEL, fg=Theme.TEXT,
                                     font=(Theme.FONT_MONO, 8), relief="flat",
                                     height=10, state="disabled")
        self.signals_list.pack(fill="both", expand=True)

    def _load_data(self):
        """Carrega dados historicos do MT5."""
        self.status_label.configure(text="Carregando...", fg=Theme.WARNING)
        self.on_status("Carregando dados historicos...")
        threading.Thread(target=self._load_thread, daemon=True).start()

    def _load_thread(self):
        try:
            from app.mt5_lock import mt5_lock
            import MetaTrader5 as mt5
            symbol = self.sym_var.get().upper()
            tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
                      "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
                      "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1}
            tf = tf_map.get(self.tf_var.get(), mt5.TIMEFRAME_H1)
            with mt5_lock:
                mt5.symbol_select(symbol, True)
                rates = mt5.copy_rates_from_pos(symbol, tf, 0, 500)
            if rates is not None and len(rates):
                self._candles = []
                for r in rates:
                    self._candles.append({
                        "time": datetime.fromtimestamp(int(r["time"])).strftime("%d/%m %H:%M"),
                        "open": float(r["open"]), "high": float(r["high"]),
                        "low": float(r["low"]), "close": float(r["close"]),
                        "volume": float(r["tick_volume"]),
                    })
                self.frame.after(0, lambda: self._on_data_loaded(True, len(self._candles)))
            else:
                self.frame.after(0, lambda: self._on_data_loaded(False, 0))
        except Exception as e:
            self.frame.after(0, lambda e=e: self._on_data_loaded(False, 0, str(e)))

    def _on_data_loaded(self, ok, n, error=None):
        if ok:
            self.status_label.configure(text=f"{n} candles carregados", fg=Theme.SUCCESS)
            self.on_status(f"Dados carregados: {n} candles")
            self._draw_chart()
        else:
            self.status_label.configure(text=f"Erro: {error or 'sem dados'}", fg=Theme.DANGER)
            self.on_status(f"Erro ao carregar dados: {error}")

    def _generate_signals(self):
        """Gera sinais baseados nos indicadores configurados."""
        if not self._candles:
            self.on_status("Carregue dados primeiro")
            return
        self._signals = []
        closes = [c["close"] for c in self._candles]
        highs = [c["high"] for c in self._candles]
        lows = [c["low"] for c in self._candles]
        volumes = [c["volume"] for c in self._candles]

        # Calcular indicadores selecionados
        ind_data = {}
        for key, var in self.ind_vars.items():
            if var.get():
                ind_data[key] = calculate(key, closes, highs, lows, volumes)

        # Gerar sinais baseados em RSI + MACD
        for i in range(26, len(closes)):
            signal = None
            # RSI oversold + MACD bullish crossover
            if "rsi" in ind_data and "macd" in ind_data:
                rsi = ind_data["rsi"]["line"]
                macd_hist = ind_data["macd"]["histogram"]
                if i > 0 and rsi[i] < 30 and macd_hist[i] > 0 and macd_hist[i - 1] <= 0:
                    signal = "BUY"
                elif i > 0 and rsi[i] > 70 and macd_hist[i] < 0 and macd_hist[i - 1] >= 0:
                    signal = "SELL"
            if signal:
                self._signals.append({
                    "index": i,
                    "type": signal,
                    "price": closes[i],
                    "time": self._candles[i]["time"],
                })

        self._update_stats()
        self._draw_chart()
        self.on_status(f"{len(self._signals)} sinais gerados")

    def _update_stats(self):
        """Atualiza estatisticas dos sinais."""
        buys = sum(1 for s in self._signals if s["type"] == "BUY")
        sells = sum(1 for s in self._signals if s["type"] == "SELL")
        self.stats_labels["Total Sinais"].configure(text=str(len(self._signals)))
        self.stats_labels["Compras"].configure(text=str(buys))
        self.stats_labels["Vendas"].configure(text=str(sells))
        self.stats_labels["Win Rate"].configure(text="--")
        self.stats_labels["Profit"].configure(text="--")

        # Atualizar lista
        self.signals_list.configure(state="normal")
        self.signals_list.delete("1.0", "end")
        for s in self._signals[-50:]:
            color = Theme.BID if s["type"] == "BUY" else Theme.ASK
            self.signals_list.insert("end", f"{s['time']} | {s['type']} | {s['price']:.2f}\n")
        self.signals_list.configure(state="disabled")

    def _draw_chart(self):
        """Desenha o grafico com candles e sinais."""
        canvas = self.chart_canvas
        canvas.delete("all")
        if not self._candles:
            canvas.create_text(canvas.winfo_width() // 2, canvas.winfo_height() // 2,
                             text="Carregue dados para visualizar", fill=Theme.TEXT_MUTED,
                             font=(Theme.FONT_FAMILY, 12))
            return

        w = canvas.winfo_width()
        h = canvas.winfo_height()
        padding = 40
        chart_h = h - padding * 2
        chart_w = w - padding * 2

        # Determinar range de preços
        visible = self._candles[-100:]  # ultimos 100 candles
        if not visible:
            return
        max_price = max(c["high"] for c in visible)
        min_price = min(c["low"] for c in visible)
        price_range = max_price - min_price if max_price != min_price else 1

        # Grid
        for i in range(5):
            y = padding + chart_h * i / 4
            price = max_price - price_range * i / 4
            canvas.create_line(padding, y, w - padding, y, fill=Theme.GRID, dash=(2, 4))
            canvas.create_text(padding - 5, y, text=f"{price:.1f}", fill=Theme.TEXT_MUTED,
                             font=(Theme.FONT_MONO, 8), anchor="e")

        # Candles
        n = len(visible)
        candle_w = max(2, chart_w / n - 1)
        for i, c in enumerate(visible):
            x = padding + i * chart_w / n + chart_w / n / 2
            y_high = padding + (max_price - c["high"]) / price_range * chart_h
            y_low = padding + (max_price - c["low"]) / price_range * chart_h
            y_open = padding + (max_price - c["open"]) / price_range * chart_h
            y_close = padding + (max_price - c["close"]) / price_range * chart_h
            color = Theme.CHART_UP if c["close"] >= c["open"] else Theme.CHART_DOWN
            canvas.create_line(x, y_high, x, y_low, fill=color)
            body_top = min(y_open, y_close)
            body_bot = max(y_open, y_close)
            body_h = max(1, body_bot - body_top)
            canvas.create_rectangle(x - candle_w / 2, body_top, x + candle_w / 2, body_bot,
                                   fill=color, outline=color)

        # Sinais
        offset = len(self._candles) - len(visible)
        for s in self._signals:
            idx = s["index"] - offset
            if 0 <= idx < n:
                x = padding + idx * chart_w / n + chart_w / n / 2
                y = padding + (max_price - s["price"]) / price_range * chart_h
                color = Theme.BID if s["type"] == "BUY" else Theme.ASK
                marker = "▲" if s["type"] == "BUY" else "▼"
                canvas.create_text(x, y - 10, text=marker, fill=color,
                                 font=(Theme.FONT_FAMILY, 12, "bold"))

    def _clear(self):
        """Limpa todos os dados."""
        self._candles = []
        self._signals = []
        self._indicators = {}
        self.chart_canvas.delete("all")
        self.status_label.configure(text="Pronto", fg=Theme.TEXT_MUTED)
        for lbl in self.stats_labels.values():
            lbl.configure(text="--")
        self.signals_list.configure(state="normal")
        self.signals_list.delete("1.0", "end")
        self.signals_list.configure(state="disabled")
