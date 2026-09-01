# -*- coding: utf-8 -*-
"""Aba Subgraph - Analise por nografos de mercado financeiro."""
import tkinter as tk
from tkinter import ttk
import asyncio
import threading


class SubgraphTab(ttk.Frame):
    """Aba de analise por subgraphs de mercado."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._setup_ui()

    def _setup_ui(self):
        """Construcao da interface."""
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)
        ttk.Label(header, text="Subgraph de Mercado Financeiro",
                  font=("Arial", 16, "bold")).pack(side="left")

        # Status
        self.status_var = tk.StringVar(value="Aguardando dados...")
        ttk.Label(header, textvariable=self.status_var,
                  font=("Arial", 10)).pack(side="right")

        # Configuracoes
        config_frame = ttk.LabelFrame(self, text="Configuracoes", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(config_frame, text="Lookback (barras):").grid(row=0, column=0, sticky="w")
        self.lookback_var = tk.StringVar(value="100")
        ttk.Entry(config_frame, textvariable=self.lookback_var,
                  width=10).grid(row=0, column=1, padx=5)

        ttk.Label(config_frame, text="Max Lag:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.max_lag_var = tk.StringVar(value="5")
        ttk.Entry(config_frame, textvariable=self.max_lag_var,
                  width=10).grid(row=0, column=3, padx=5)

        # Botoes
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(btn_frame, text="Iniciar Analise",
                   command=self._start_analysis).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Detectar Regime",
                   command=self._detect_regime).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Exportar JSON",
                   command=self._export_json).pack(side="left", padx=5)

        # Resultados
        result_frame = ttk.LabelFrame(self, text="Resultados", padding=10)
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.result_text = tk.Text(result_frame, height=20, width=80)
        self.result_text.pack(fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.result_text.config(yscrollcommand=scrollbar.set)

    def _start_analysis(self):
        """Inicia analise de subgraph em thread separada."""
        self.status_var.set("Analisando...")
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()

    def _run_analysis(self):
        """Executa a analise (thread-safe)."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._async_analysis())
            self._update_result(result)
        except Exception as e:
            self.status_var.set(f"Erro: {e}")

    async def _async_analysis(self):
        """Analise assincrona."""
        from mcp.subgrp.financial_graph import FinancialSubgraph

        lookback = int(self.lookback_var.get())
        max_lag = int(self.max_lag_var.get())

        fg = FinancialSubgraph(lookback_bars=lookback, max_lag=max_lag)

        # Dados simulados (placeholder - conectar ao MT5 no futuro)
        import pandas as pd
        import numpy as np

        dates = pd.date_range("2024-01-01", periods=200, freq="h")
        df = pd.DataFrame({
            "open": np.random.randn(200).cumsum() + 100,
            "high": np.random.randn(200).cumsum() + 101,
            "low": np.random.randn(200).cumsum() + 99,
            "close": np.random.randn(200).cumsum() + 100,
            "volume": np.random.randint(100, 1000, 200),
        }, index=dates)

        await fg.ingest_asset("XAUUSD", df, "metal", "H1")
        edges = await fg.compute_correlations()
        regime = await fg.detect_regime_shift()

        return dict(regime=regime, edges=len(edges), nodes=len(fg.nodes))

    def _update_result(self, result):
        """Atualiza area de resultado."""
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"Regime: {result['regime']['regime']}\n")
        self.result_text.insert("end", f"Volatilidade media: {result['regime']['avg_volatility']:.4f}\n")
        self.result_text.insert("end", f"Momentum medio: {result['regime']['avg_momentum']:.4f}\n")
        self.result_text.insert("end", f"Nos: {result['nodes']}\n")
        self.result_text.insert("end", f"Arestas: {result['edges']}\n")
        self.status_var.set("Analise concluida")

    def _detect_regime(self):
        """Detecta regime de mercado."""
        self._start_analysis()

    def _export_json(self):
        """Exporta resultado em JSON."""
        import json
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if filename:
            data = self.result_text.get("1.0", "end")
            with open(filename, "w") as f:
                json.dump({"result": data}, f, indent=2)
            self.status_var.set(f"Exportado: {filename}")
