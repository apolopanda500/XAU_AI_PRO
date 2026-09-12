# -*- coding: utf-8 -*-
"""Aba Sistema - monitoramento e configuracao de CPU/RAM/FPS/temperatura.

Painel profissional em tempo real:
  - CPU: uso %, nucleos, prioridade, afinidade, FPS da GUI
  - RAM: total / livre / usada / % uso
  - Temperatura (se sensor disponivel)
  - Uso de disco e tempo ligado (uptime)
  - Edicao: prioridade, afinidade, nucleos p/ modelo, RAM max %, temp alerta
Auto-refresh com intervalo configuravel (default 2s).
"""
from __future__ import annotations

import ctypes
import threading
import time
import tkinter as tk
from datetime import datetime
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.cpu import (affinity_mask, apply_cpu_options, apply_model_limits,
                     current_priority, logical_cores, memory_info,
                     model_max_ram_mb, model_n_jobs, parse_affinity,
                     set_affinity, set_priority, temperature_c, cpu_usage,
                     system_specs, model_presets, MODEL_PRESET_ORDER,
                     current_model_preset, preset_ram_mb, set_model_preset,
                     core_frequencies_mhz, battery_status)
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme
from app.utils.async_ui import run_bg


class SystemTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._running = False
        self._last_fps_ts = time.time()
        self._fps_count = 0
        self._fps_value = 0.0
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        from app.components.banner import TabBanner
        TabBanner(self.frame, "system")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Sistema", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Monitoramento e desempenho em tempo real",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)
        self.mode_lbl = tk.Label(header, text="Atualizando: 2s", bg=Theme.BG,
                                 fg=Theme.PRIMARY, font=(Theme.FONT_FAMILY, 9, "bold"))
        self.mode_lbl.pack(side="right")

        # ---- Monitoramento -----
        mon = Card(self.frame, title="Monitoramento em tempo real")
        mon.pack(fill="x", padx=24, pady=10)
        grid = tk.Frame(mon.body, bg=Theme.CARD)
        grid.pack(fill="x", padx=8, pady=8)
        self.stats: dict[str, tk.Label] = {}
        keys = [
            ("cpu_uso", "CPU uso %"), ("cpu_nucleos", "Nucleos"),
            ("cpu_prioridade", "Prioridade"), ("cpu_afinidade", "Afinidade"),
            ("fps", "FPS (GUI)"), ("ram_uso", "RAM uso %"),
            ("ram_total", "RAM total"), ("ram_livre", "RAM livre"),
            ("ram_usada", "RAM usada"), ("temp", "Temperatura"),
            ("disco", "Disco (C:) livre"), ("uptime", "Uptime sistema"),
            ("proc", "Processos"), ("model_njobs", "Nucleos p/ modelo"),
            ("model_ram", "RAM limite modelos"),
        ]
        for i, (key, label) in enumerate(keys):
            r, c = divmod(i, 3)
            tk.Label(grid, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 9)).grid(row=r, column=c * 2, sticky="w", padx=(4, 8), pady=3)
            val = tk.Label(grid, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_MONO if hasattr(Theme, 'FONT_MONO') else Theme.FONT_FAMILY, 9, "bold"))
            val.grid(row=r, column=c * 2 + 1, sticky="w", padx=4, pady=3)
            self.stats[key] = val

        ops = tk.Frame(mon.body, bg=Theme.CARD)
        ops.pack(fill="x", padx=8, pady=(0, 8))
        tk.Label(ops, text="Intervalo (s)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        self.interval_entry = tk.Entry(ops, width=6, bg=Theme.PANEL, fg=Theme.TEXT,
                                       relief="flat", highlightbackground=Theme.BORDER,
                                       highlightthickness=1)
        self.interval_entry.insert(0, "2")
        self.interval_entry.pack(side="left", padx=4)
        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(ops, text="Auto atualizar", variable=self.auto_var, bg=Theme.CARD,
                       fg=Theme.TEXT, selectcolor=Theme.PANEL, activebackground=Theme.CARD,
                       font=(Theme.FONT_FAMILY, 9)).pack(side="left", padx=10)
        PrimaryButton(ops, text="Atualizar agora", command=self.refresh_now, width=14).pack(side="left", padx=6)

        # ---- Mini informacao de CPU (linha compacta de diagnostico) ------
        self.cpu_mini = tk.Label(mon.body, text="CPU: aguardando leitura...",
                                 bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                 font=(Theme.FONT_FAMILY, 8), anchor="w")
        self.cpu_mini.pack(fill="x", padx=8, pady=(2, 6))

        # ---- Specs da maquina ----
        spec_card = Card(self.frame, title="Specs da Maquina (hardware detectado)")
        spec_card.pack(fill="x", padx=24, pady=6)
        sfg = tk.Frame(spec_card.body, bg=Theme.CARD)
        sfg.pack(fill="x", padx=8, pady=8)
        self.spec_labels: dict[str, tk.Label] = {}
        spec_keys = [
            ("cpu_name", "CPU"), ("cpu_cores", "Nucleos (fisicos/logicos)"),
            ("ram_total", "RAM total"), ("gpu", "GPU"),
            ("freq", "Frequencia CPU"), ("battery", "Bateria / AC"),
            ("disco", "Disco (total/livre)"), ("os", "Sistema Operacional"),
            ("arq", "Arquitetura"), ("host", "Hostname"),
        ]
        for i, (key, label) in enumerate(spec_keys):
            r, c = divmod(i, 2)
            tk.Label(sfg, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                     font=(Theme.FONT_FAMILY, 8)).grid(row=r, column=c * 2, sticky="w", padx=(4, 6), pady=2)
            val = tk.Label(sfg, text="--", bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_FAMILY, 9, "bold"), anchor="w")
            val.grid(row=r, column=c * 2 + 1, sticky="w", padx=4, pady=2)
            self.spec_labels[key] = val
        SecondaryButton(spec_card.body, text="Reler hardware",
                        command=self.load_specs, width=16).pack(anchor="e", padx=8, pady=(0, 8))

        self.load_specs()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Specs da maquina + Presets
    # ------------------------------------------------------------------
    def load_specs(self) -> None:
        """Le as specs da maquina e atualiza o card."""
        self.spec_labels["cpu_name"].configure(text="Lendo...", fg=Theme.TEXT_MUTED)

        def worker() -> None:
            s = system_specs()
            self.frame.after(0, lambda: self._apply_specs(s))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_specs(self, s: dict) -> None:
        def st(key, text):
            w = self.spec_labels.get(key)
            if w:
                w.configure(text=text, fg=Theme.TEXT)
        st("cpu_name", str(s.get("cpu_name", "--")))
        st("cpu_cores", f"{s.get('cpu_cores_fisicos')} / {s.get('cpu_cores_logicos')}")
        ram = s.get("ram_total_mb", 0)
        st("ram_total", f"{ram:,} MB ({ram / 1024:.1f} GB)".replace(",", "."))
        st("gpu", str(s.get("gpu_name", "--")))
        freq = s.get("freq_mhz", 0)
        st("freq", f"{freq / 1000:.2f} GHz" if freq else "N/A")
        try:
            batt = battery_status()
        except Exception:
            batt = {}
        if batt.get("ac") is not None and batt.get("pct", -1) >= 0:
            label = "AC" if batt.get("ac") == 1 else f"Bateria {batt.get('pct')}%"
            st("battery", label)
        else:
            st("battery", "N/A")
        if s.get("disco_total_gb", -1) >= 0:
            st("disco", f"{s.get('disco_total_gb')} GB / {s.get('disco_livre_gb')} GB livre")
        else:
            st("disco", "N/A")
        st("os", f"{s.get('os_name')} {s.get('os_version')}")
        st("arq", str(s.get("arquitetura", "--")))
        st("host", str(s.get("hostname", "--")))

    def _render_preset_list(self) -> None:
        presets = model_presets(get_config())
        lines = []
        for name in MODEL_PRESET_ORDER:
            mb = presets.get(name, 0)
            lines.append(f"{name:12} -> {mb:,} MB ({mb / 1024:.1f} GB)".replace(",", "."))
        self.preset_list_lbl.configure(text="\n".join(lines))

    def apply_preset(self) -> None:
        c = get_config()
        name = self.preset_var.get()
        if set_model_preset(c, name):
            mb = preset_ram_mb(c)
            self.preset_info.configure(
                text=f"Modelo {name} ativo: RAM <= {mb:,} MB ({mb / 1024:.1f} GB)".replace(",", "."),
                fg=Theme.SUCCESS)
            self.ram_entry.delete(0, "end")
            self.ram_entry.insert(0, "%.0f" % (mb * 100.0 / (memory_info().get("total_mb", 4096) or 4096)))
            self.on_status(f"Preset {name} aplicado (RAM {mb} MB)")
            self.refresh_now()
        else:
            self.preset_info.configure(text=f"Preset '{name}' invalido", fg=Theme.DANGER)

    def edit_presets(self) -> None:
        """Abre janela simples para editar a RAM (MB) de cada preset."""
        from tkinter import simpledialog, messagebox
        presets = model_presets(get_config())
        c = get_config()
        changed = False
        for name in MODEL_PRESET_ORDER:
            atual = presets.get(name, 0)
            resp = simpledialog.askinteger(
                "Preset " + name,
                f"RAM maxima (MB) para o modelo {name}:\n(atual: {atual} MB)\nSugestoes: X1 Lite=1024, X1=2048, X2=4096, X3=8192, X4=12288, X5 Pro=16384, X5 Ultra=24576",
                initialvalue=atual, minvalue=256, maxvalue=262144,
                parent=self.frame)
            if resp is not None and resp != atual:
                presets[name] = resp
                changed = True
        if changed:
            c.set("cpu", "model_presets", value=presets)
            self._render_preset_list()
            self.on_status("Presets de RAM atualizados")

    def start_monitor(self) -> None:
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop_monitor(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                interval = 2
                try:
                    interval = max(1, int(self.interval_entry.get()))
                except ValueError:
                    pass
                self.refresh_now()
                time.sleep(interval)
            except Exception:
                time.sleep(5)

    def _aff_value(self) -> str:
        aff = self.aff_var.get()
        return (self.aff_entry.get().strip() or "todos") if aff == "personalizado" else aff

    def apply_now(self) -> None:
        c = get_config()
        ok_p = set_priority(self.prio_var.get())
        mask = parse_affinity(self._aff_value())
        ok_a = bool(mask) and set_affinity(mask)
        n, ram = apply_model_limits(c)
        msg = f"Prioridade {'OK' if ok_p else 'FALHOU'} | Afinidade {'OK' if ok_a else 'FALHOU'} | Modelos: {n} nucleo(s), RAM <= {ram} MB"
        self.cfg_status.configure(text=msg)
        self.on_status(msg)
        self.refresh_now()

    def save_config(self) -> None:
        c = get_config()
        c.set("cpu", "priority", value=self.prio_var.get())
        aff = self._aff_value()
        c.set("cpu", "affinity", value=aff)
        c.set("cpu", "model_cores", value=self.cores_entry.get().strip() or "auto")
        try:
            c.set("cpu", "max_ram_pct", value=float(self.ram_entry.get()))
        except ValueError:
            pass
        try:
            c.set("cpu", "temp_warn_c", value=float(self.temp_entry.get()))
        except ValueError:
            pass
        self.cfg_status.configure(text="Configuracao salva")
        self.on_status("Configuracao de sistema salva")

    def use_all_cores(self) -> None:
        self.cores_entry.delete(0, "end")
        self.cores_entry.insert(0, "auto")
        c = get_config()
        c.set("cpu", "model_cores", value="auto")
        apply_model_limits(c)

    # ------------------------------------------------------------------
    def refresh_now(self) -> None:
        """Coleta dados em thread e atualiza a GUI com after (nao trava)."""
        run_bg(self.frame, self._collect, self._apply, on_error=lambda _exc: None)

    def _collect(self) -> dict:
        mem = memory_info()
        cores = logical_cores()
        temp = temperature_c()
        usage = cpu_usage(250)
        disks = ctypes.c_ulonglong(0)
        try:
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                "C:\\", None, None, ctypes.byref(disks))
            free_gb = disks.value / (1024 ** 3)
        except Exception:
            free_gb = -1
        up = time.time() - ctypes.windll.kernel32.GetTickCount64() / 1000.0 if hasattr(ctypes.windll.kernel32, "GetTickCount64") else 0
        up_h = up / 3600.0
        try:
            import os
            procs = len(os.popen("tasklist").read().splitlines()) - 4
        except Exception:
            procs = -1
        # FPS real medido pelo relógio da GUI, sem acessar Tk nesta thread.
        # FPS real medido pelo relogio da GUI, sem acessar Tk nesta thread.
        from app.runtime_metrics import get_gui_fps
        self._fps_value = get_gui_fps()
        # Flags OK/FALHOU da aplicacao de prioridade/afinidade (idempotente).
        try:
            ok_p, ok_a = apply_cpu_options(get_config())
        except Exception:
            ok_p = ok_a = False
        self._cpu_ok = (bool(ok_p), bool(ok_a))
        return {
            "cpu_uso": usage, "cpu_nucleos": cores,
            "cpu_prioridade": current_priority(),
            "cpu_afinidade": f"0x{affinity_mask():X}",
            "fps": self._fps_value,
            "ram_uso": mem.get("usage_pct", 0),
            "ram_total": mem.get("total_mb", 0),
            "ram_livre": mem.get("free_mb", 0),
            "ram_usada": mem.get("used_mb", 0),
            "temp": temp, "disco": free_gb,
            "uptime": up_h, "proc": procs,
            "model_njobs": model_n_jobs(get_config()),
            "model_ram": model_max_ram_mb(get_config()),
            "cpu_ok": getattr(self, "_cpu_ok", (False, False)),
        }

    def _apply(self, d: dict) -> None:
        def st(key, text, color=None):
            w = self.stats.get(key)
            if w:
                w.configure(text=text, fg=color or Theme.TEXT)
        st("cpu_uso", f"{d['cpu_uso']:.1f}%")
        st("cpu_nucleos", str(d["cpu_nucleos"]))
        st("cpu_prioridade", str(d["cpu_prioridade"]).capitalize())
        st("cpu_afinidade", d["cpu_afinidade"])
        fps = d["fps"]
        st("fps", f"{fps:.1f}" if fps > 0 else "--")
        st("ram_uso", f"{d['ram_uso']:.1f}%")
        st("ram_total", f"{d['ram_total']:,} MB".replace(",", "."))
        st("ram_livre", f"{d['ram_livre']:,} MB".replace(",", "."))
        st("ram_usada", f"{d['ram_usada']:,} MB".replace(",", "."))
        t = d["temp"]
        warn = float(self.temp_entry.get()) if self.temp_entry.get().strip() else 85
        if t < 0:
            st("temp", "N/A (sem sensor)", Theme.TEXT_MUTED)
        else:
            st("temp", f"{t:.1f} C", Theme.WARNING if t >= warn else Theme.SUCCESS)
        if d["disco"] >= 0:
            st("disco", f"{d['disco']:.1f} GB")
        else:
            st("disco", "N/A")
        st("uptime", f"{d['uptime']:.1f} h")
        st("proc", str(d["proc"]) if d["proc"] >= 0 else "--")
        st("model_njobs", str(d["model_njobs"]))
        st("model_ram", f"{d['model_ram']:,} MB".replace(",", "."))
        try:
            self.mode_lbl.configure(text=f"Atualizando: {self.interval_entry.get()}s")
        except Exception:
            pass
        # Mini informacao compacta de CPU na pagina de configuracao.
        try:
            ok_p, ok_a = d.get("cpu_ok", (False, False))
            ram_mb = int(d.get("model_ram", 0) or 0)
            self.cpu_mini.configure(
                text=(f"CPU: prioridade {'ok' if ok_p else 'falhou'} · "
                      f"afinidade {'ok' if ok_a else 'falhou'} · "
                      f"modelos {d.get('model_njobs', '--')} nucleo(s) · "
                      f"RAM {ram_mb:,} MB").replace(",", "."),
                fg=Theme.SUCCESS if (ok_p and ok_a) else Theme.WARNING,
            )
        except Exception:
            pass
