# -*- coding: utf-8 -*-
"""Aba de análise de relações entre ativos, somente leitura."""
from __future__ import annotations

import asyncio
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable

import pandas as pd

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.theme.mexc import Theme
from app.utils.async_ui import run_bg

ASSET_CLASSES = {
    "XAUUSD": "metal", "BTCUSD": "crypto", "ETHUSD": "crypto",
    "EURUSD": "currency", "GBPUSD": "currency", "USDJPY": "currency",
    "AUDUSD": "currency", "SPX500": "index", "US30": "index",
}


class SubgraphTab:
    """Consulta candles do MT5; não envia ordens de operação."""

    def __init__(self, parent: tk.Widget, robot: Any, market: Any, on_status: Callable[[str], None]) -> None:
        self.robot, self.market, self.on_status = robot, market, on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self._last_export: dict[str, Any] | None = None
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Subgraph de Mercado", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        self.status_var = tk.StringVar(value="Somente análise — nenhuma ordem será enviada")
        tk.Label(header, textvariable=self.status_var, bg=Theme.BG, fg=Theme.PRIMARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="right")

        controls = Card(self.frame, title="Configuração")
        controls.pack(fill="x", padx=24, pady=8)
        tk.Label(controls.body, text="Símbolos", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, padx=8, pady=8)
        self.symbols_var = tk.StringVar(value="XAUUSD,BTCUSD,ETHUSD,EURUSD")
        tk.Entry(controls.body, textvariable=self.symbols_var, width=42, bg=Theme.PANEL,
                 fg=Theme.TEXT, insertbackground=Theme.TEXT, relief="flat").grid(row=0, column=1, padx=8)
        tk.Label(controls.body, text="Timeframe", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=2, padx=8)
        self.timeframe_var = tk.StringVar(value="M5")
        tk.OptionMenu(controls.body, self.timeframe_var, "M1", "M5", "M15", "M30", "H1", "H4", "D1").grid(row=0, column=3, padx=8)
        tk.Label(controls.body, text="Candles", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=4, padx=8)
        self.bars_var = tk.StringVar(value="300")
        tk.Entry(controls.body, textvariable=self.bars_var, width=8, bg=Theme.PANEL,
                 fg=Theme.TEXT, insertbackground=Theme.TEXT, relief="flat").grid(row=0, column=5, padx=8)
        PrimaryButton(controls.body, text="Analisar MT5", command=self.analyze, width=16).grid(row=0, column=6, padx=8)
        SecondaryButton(controls.body, text="Exportar JSON", command=self.export_json, width=14).grid(row=0, column=7, padx=8)

        output = Card(self.frame, title="Resultado")
        output.pack(fill="both", expand=True, padx=24, pady=8)
        self.result = tk.Text(output.body, bg=Theme.PANEL, fg=Theme.TEXT, relief="flat", wrap="word", height=22)
        self.result.pack(fill="both", expand=True, padx=8, pady=8)
        self.result.insert("end", "Configure os ativos e clique em “Analisar MT5”.\n")
        self.result.configure(state="disabled")

    def _write(self, text: str) -> None:
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text)
        self.result.configure(state="disabled")

    def _inputs(self) -> tuple[list[str], str, int]:
        symbols = [item.strip().upper() for item in self.symbols_var.get().split(",") if item.strip()]
        if not symbols:
            raise ValueError("Informe pelo menos um símbolo")
        bars = max(30, min(int(self.bars_var.get()), 5000))
        return symbols, self.timeframe_var.get().upper(), bars

    def analyze(self) -> None:
        self.status_var.set("Lendo candles do MT5…")
        run_bg(self.frame, self._worker, self._apply, self._error)

    def _read_candles(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        if not self.robot.connected and not self.robot.connect():
            raise RuntimeError(f"MT5 não conectado: {self.robot.last_error or 'indisponível'}")
        mt5 = self.robot.mt5
        mt5_timeframe = getattr(mt5, f"TIMEFRAME_{timeframe}", None)
        if mt5_timeframe is None:
            raise ValueError(f"Timeframe não suportado: {timeframe}")
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Símbolo indisponível no MT5: {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
        if rates is None or len(rates) < 30:
            raise RuntimeError(f"Poucos candles disponíveis para {symbol}")
        data = pd.DataFrame(rates)
        data["time"] = pd.to_datetime(data["time"], unit="s", utc=True)
        return data.set_index("time")

    def _worker(self) -> dict[str, Any]:
        from mcp.subgrp.financial_graph import FinancialSubgraph

        symbols, timeframe, bars = self._inputs()
        graph = FinancialSubgraph(bars, 5)
        loaded: list[str] = []
        failures: dict[str, str] = {}
        for symbol in symbols:
            try:
                candles = self._read_candles(symbol, timeframe, bars)
                asyncio.run(graph.ingest_asset(symbol, candles, ASSET_CLASSES.get(symbol, "unknown"), timeframe))
                loaded.append(symbol)
            except Exception as exc:  # noqa: BLE001
                failures[symbol] = str(exc)
        if not loaded:
            raise RuntimeError("Nenhum ativo pôde ser carregado do MT5")
        edges = asyncio.run(graph.compute_correlations())
        regime = asyncio.run(graph.detect_regime_shift())
        export = asyncio.run(graph.to_dict())
        export.update({"loaded_symbols": loaded, "failures": failures, "regime": regime})
        return {"loaded": loaded, "failures": failures, "edges": edges, "regime": regime, "export": export}

    def _apply(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        self._last_export = payload["export"]
        regime = payload["regime"]
        lines = [
            "MODO SOMENTE ANÁLISE — nenhuma ordem foi enviada.",
            f"Ativos carregados: {', '.join(payload['loaded'])}",
            f"Regime: {regime['regime']}",
            f"Volatilidade média: {regime['avg_volatility']:.6f}",
            f"Momentum médio: {regime['avg_momentum']:.6f}",
            "", "Correlações:",
        ]
        lines.extend(
            f"• {edge.source} × {edge.target}: {edge.correlation:+.3f} | "
            f"lag {edge.lag:+d} | {edge.strength} | {edge.samples} amostras"
            for edge in payload["edges"]
        )
        if not payload["edges"]:
            lines.append("• São necessários dois ou mais ativos válidos.")
        if payload["failures"]:
            lines.extend(["", "Ativos não carregados:"])
            lines.extend(f"• {symbol}: {message}" for symbol, message in payload["failures"].items())
        self._write("\n".join(lines))
        self.status_var.set("Análise concluída")
        self.on_status(f"Subgraph: {len(payload['loaded'])} ativos analisados")

    def _error(self, exc: Exception) -> None:
        self.status_var.set("Análise não concluída")
        self._write(f"Não foi possível ler o MT5.\n\n{exc}\n\nNenhuma ordem foi enviada.")
        self.on_status("Subgraph: erro de leitura MT5")

    def export_json(self) -> None:
        if not self._last_export:
            self.status_var.set("Execute uma análise antes de exportar")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".json", initialfile="subgraph_report.json", filetypes=[("JSON", "*.json")]
        )
        if filename:
            Path(filename).write_text(json.dumps(self._last_export, indent=2, ensure_ascii=False), encoding="utf-8")
            self.status_var.set(f"Relatório exportado: {Path(filename).name}")