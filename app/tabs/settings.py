"""
Aba Configuracoes do app XAU_AI_PRO.
"""
from __future__ import annotations

import tkinter as tk
import shutil
import threading

from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton, AccentButton
from app.config_manager import get_config
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


class SettingsTab:
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
        TabBanner(self.frame, "settings")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Configuracoes", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")

        # MT5
        mt5_card = Card(self.frame, title="MetaTrader 5")
        mt5_card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(mt5_card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Caminho terminal", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.entry_terminal = tk.Entry(form, width=70, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                       relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_terminal.insert(0, get_config().get("mt5", "terminal_path", default=""))
        self.entry_terminal.grid(row=0, column=1, padx=4, pady=4)
        SecondaryButton(form, text="Procurar", command=self.browse_terminal, width=10).grid(row=0, column=2, padx=4)
        tk.Label(form, text="Magic Number", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        self.entry_magic = tk.Entry(form, width=20, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                                    relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.entry_magic.insert(0, str(get_config().get("mt5", "magic_number", default=2026001)))
        self.entry_magic.grid(row=1, column=1, sticky="w", padx=4)

        # Trading
        trade_card = Card(self.frame, title="Trading")
        trade_card.pack(fill="x", padx=24, pady=10)
        tf = tk.Frame(trade_card.body, bg=Theme.CARD)
        tf.pack(fill="x", padx=8, pady=8)
        labels = [("Risco %", "risk_percent"), ("Max lote", "max_lot"),
                  ("SL pontos", "stop_loss_points"), ("TP pontos", "take_profit_points"),
                  ("Spread max", "max_spread_points"), ("Max DD %", "max_drawdown_pct")]
        self.trading_entries: dict[str, tk.Entry] = {}
        for i, (label, key) in enumerate(labels):
            tk.Label(tf, text=label, bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=i//3, column=(i%3)*2, padx=4, pady=4, sticky="w")
            e = tk.Entry(tf, width=14, bg=Theme.PANEL, fg=Theme.TEXT, insertbackground=Theme.TEXT,
                         relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
            e.insert(0, str(get_config().get("trading", key, default="")))
            e.grid(row=i//3, column=(i%3)*2+1, padx=4, pady=4, sticky="w")
            self.trading_entries[key] = e

        # Desempenho (CPU)
        cpu_card = Card(self.frame, title="Desempenho (CPU)")
        cpu_card.pack(fill="x", padx=24, pady=10)
        cf = tk.Frame(cpu_card.body, bg=Theme.CARD)
        cf.pack(fill="x", padx=8, pady=8)

        from app.cpu import affinity_mask, logical_cores  # noqa: PLC0415
        tk.Label(cf,
                 text=f"Nucleos logicos: {logical_cores()} | Mascara atual: {affinity_mask():#x}",
                 bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 9)).grid(row=0, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 8))

        self.cpu_priority_var = tk.StringVar(value=str(get_config().get("cpu", "priority", default="normal")))
        self.cpu_affinity_var = tk.StringVar(value=str(get_config().get("cpu", "affinity", default="todos")))
        self.cpu_cores_var = tk.StringVar(value=str(get_config().get("cpu", "model_cores", default="auto")))
        self.cpu_ram_pct_var = tk.StringVar(value=str(get_config().get("cpu", "max_ram_pct", default=80)))
        self.cpu_temp_warn_var = tk.StringVar(value=str(get_config().get("cpu", "temp_warn_c", default=85)))

        tk.Label(cf, text="Prioridade", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        tk.OptionMenu(cf, self.cpu_priority_var, "baixa", "normal", "alta").grid(row=1, column=1, sticky="w", padx=4)

        tk.Label(cf, text="Nucleos", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=2, sticky="w", padx=4)
        tk.OptionMenu(cf, self.cpu_affinity_var, "todos", "metade", "quarto", "um", "personalizado").grid(row=1, column=3, sticky="w", padx=4)

        tk.Label(cf, text="Cores personalizados (ex.: 0,2-3)", bg=Theme.CARD,
                 fg=Theme.TEXT_SECONDARY).grid(row=2, column=0, sticky="w", padx=4, pady=(8, 4))
        self.cpu_affinity_entry = tk.Entry(cf, width=24, bg=Theme.PANEL, fg=Theme.TEXT,
                                           insertbackground=Theme.TEXT, relief="flat",
                                           highlightbackground=Theme.BORDER, highlightthickness=1)
        self.cpu_affinity_entry.grid(row=2, column=1, columnspan=2, sticky="w", padx=4, pady=(8, 4))
        AccentButton(cf, text="Aplicar CPU agora", command=self.apply_cpu, width=18).grid(row=2, column=3, padx=4, pady=(8, 4))

        # Linha 3: recursos dos modelos
        tk.Label(cf, text="Nucleos p/ modelo", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=3, column=0, sticky="w", padx=4, pady=(8, 4))
        self.cpu_cores_entry = tk.Entry(cf, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                        insertbackground=Theme.TEXT, relief="flat",
                                        highlightbackground=Theme.BORDER, highlightthickness=1)
        self.cpu_cores_entry.insert(0, self.cpu_cores_var.get())
        self.cpu_cores_entry.grid(row=3, column=1, sticky="w", padx=4, pady=(8, 4))
        tk.Label(cf, text="auto = todos", bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                 font=(Theme.FONT_FAMILY, 8)).grid(row=3, column=2, sticky="w", padx=4)

        tk.Label(cf, text="RAM max %", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=4, column=0, sticky="w", padx=4, pady=(4, 4))
        self.cpu_ram_entry = tk.Entry(cf, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                      insertbackground=Theme.TEXT, relief="flat",
                                      highlightbackground=Theme.BORDER, highlightthickness=1)
        self.cpu_ram_entry.insert(0, self.cpu_ram_pct_var.get())
        self.cpu_ram_entry.grid(row=4, column=1, sticky="w", padx=4, pady=(4, 4))
        tk.Label(cf, text="Temp alerta °C", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=4, column=2, sticky="w", padx=4)
        self.cpu_temp_entry = tk.Entry(cf, width=10, bg=Theme.PANEL, fg=Theme.TEXT,
                                       insertbackground=Theme.TEXT, relief="flat",
                                       highlightbackground=Theme.BORDER, highlightthickness=1)
        self.cpu_temp_entry.insert(0, self.cpu_temp_warn_var.get())
        self.cpu_temp_entry.grid(row=4, column=3, sticky="w", padx=4)

        self.cpu_status_label = tk.Label(cf, text="", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                         font=(Theme.FONT_FAMILY, 9))
        self.cpu_status_label.grid(row=5, column=0, columnspan=4, sticky="w", padx=4, pady=(6, 0))

        resources_card = Card(self.frame, title="Diagnostico do Desk")
        resources_card.pack(fill="x", padx=24, pady=10)
        self.resources_label = tk.Label(resources_card.body, text="Carregue o diagnostico sob demanda.",
                                        bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                        justify="left", anchor="w", font=(Theme.FONT_FAMILY, 9))
        self.resources_label.pack(fill="x", padx=12, pady=(10, 6))
        SecondaryButton(resources_card.body, text="Atualizar diagnostico", command=self.refresh_resources,
                        width=20).pack(anchor="w", padx=12, pady=(0, 10))

        profile_card = Card(self.frame, title="Perfil Operacional")
        profile_card.pack(fill="x", padx=24, pady=10)
        profile_row = tk.Frame(profile_card.body, bg=Theme.CARD)
        profile_row.pack(fill="x", padx=12, pady=10)
        self.desk_profile_var = tk.StringVar(value=str(get_config().get("cpu", "desk_profile", default="Equilibrado")))
        tk.Label(profile_row, text="Perfil", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(side="left")
        tk.OptionMenu(profile_row, self.desk_profile_var, "Conservador", "Equilibrado", "Baixa latencia").pack(side="left", padx=8)
        AccentButton(profile_row, text="Aplicar perfil", command=self.apply_desk_profile, width=16).pack(side="left", padx=4)
        tk.Label(profile_card.body, text="Ajusta somente prioridade, afinidade e limites do XAU AI PRO. Nunca envia ordens nem altera o Windows globalmente.",
                 bg=Theme.CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 8)).pack(anchor="w", padx=12, pady=(0, 10))

        storage_card = Card(self.frame, title="Armazenamento e Auditoria")
        storage_card.pack(fill="x", padx=24, pady=10)
        self.storage_label = tk.Label(storage_card.body, text="Lendo armazenamento local...", bg=Theme.CARD,
                                      fg=Theme.TEXT_SECONDARY, justify="left", anchor="w", font=(Theme.FONT_FAMILY, 9))
        self.storage_label.pack(fill="x", padx=12, pady=(10, 6))
        SecondaryButton(storage_card.body, text="Atualizar armazenamento", command=self.refresh_storage,
                        width=22).pack(anchor="w", padx=12, pady=(0, 10))

        # Modelos IA - CDN Vercel (download sob demanda)
        models_card = Card(self.frame, title="Modelos IA - CDN Vercel")
        models_card.pack(fill="x", padx=24, pady=10)
        mf = tk.Frame(models_card.body, bg=Theme.CARD)
        mf.pack(fill="x", padx=8, pady=8)
        tk.Label(mf, text="URL base (manifest.json)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.models_url_entry = tk.Entry(mf, width=60, bg=Theme.PANEL, fg=Theme.TEXT, relief="flat",
                                         highlightbackground=Theme.BORDER, highlightthickness=1)
        self.models_url_entry.insert(0, get_config().get("integrations", "models", "base_url", default=""))
        self.models_url_entry.grid(row=0, column=1, columnspan=3, padx=4, pady=3)
        tk.Label(mf, text="API key (opcional)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.models_key_entry = tk.Entry(mf, width=60, bg=Theme.PANEL, fg=Theme.TEXT, show="*",
                                         relief="flat", highlightbackground=Theme.BORDER, highlightthickness=1)
        self.models_key_entry.insert(0, get_config().get("integrations", "models", "api_key", default=""))
        self.models_key_entry.grid(row=1, column=1, columnspan=3, padx=4, pady=3)
        self.models_res = tk.Label(mf, text="", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                                   font=(Theme.FONT_FAMILY, 9), anchor="w")
        self.models_res.grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))
        SecondaryButton(mf, text="Testar manifest", command=self.test_models, width=16).grid(row=3, column=0, padx=4, pady=4, sticky="w")
        AccentButton(mf, text="Salvar modelos", command=self.save_models, width=16).grid(row=3, column=1, padx=4, pady=4, sticky="w")

        # Botoes
        btn_row = tk.Frame(self.frame, bg=Theme.BG)
        btn_row.pack(fill="x", padx=24, pady=20)
        PrimaryButton(btn_row, text="Salvar Configuracoes", command=self.save, width=22).pack(side="left", padx=4)
        AccentButton(btn_row, text="Testar Conexao MT5", command=self.test_mt5, width=20).pack(side="left", padx=8)

    def browse_terminal(self) -> None:
        fd = getattr(tk, "filedialog", None)
        if fd is None:
            self.on_status("Selecao de arquivo indisponivel neste build")
            return
        path = fd.askopenfilename(filetypes=[("Executavel", "*.exe")])
        if path:
            self.entry_terminal.delete(0, "end")
            self.entry_terminal.insert(0, path)

    def save(self) -> None:
        c = get_config()
        c.set("mt5", "terminal_path", value=self.entry_terminal.get())
        c.set("mt5", "magic_number", value=int(self.entry_magic.get()))
        for key, entry in self.trading_entries.items():
            try:
                c.set("trading", key, value=float(entry.get()))
            except ValueError:
                pass
        c.set("cpu", "priority", value=self.cpu_priority_var.get())
        aff = self.cpu_affinity_var.get()
        if aff == "personalizado":
            aff = self.cpu_affinity_entry.get().strip() or "todos"
        c.set("cpu", "affinity", value=aff)
        # Limites de recursos dos modelos
        c.set("cpu", "model_cores", value=self.cpu_cores_entry.get().strip() or "auto")
        try:
            c.set("cpu", "max_ram_pct", value=float(self.cpu_ram_entry.get()))
        except ValueError:
            pass
        try:
            c.set("cpu", "temp_warn_c", value=float(self.cpu_temp_entry.get()))
        except ValueError:
            pass
        self.on_status("Configuracoes salvas")

    def _affinity_value(self) -> str:
        aff = self.cpu_affinity_var.get()
        if aff == "personalizado":
            return self.cpu_affinity_entry.get().strip() or "todos"
        return aff

    def refresh_resources(self) -> None:
        self.resources_label.configure(text="Lendo recursos do desk...", fg=Theme.TEXT_SECONDARY)

        def worker() -> None:
            from app.cpu import memory_info, system_specs
            specs = system_specs()
            memory = memory_info()
            text = (f"CPU: {specs.get('cpu_name', 'N/D')} | "
                    f"GPU: {specs.get('gpu_name', 'N/D')}\n"
                    f"RAM: {memory.get('used_mb', 0):,} / {memory.get('total_mb', 0):,} MB "
                    f"({memory.get('usage_pct', 0):.0f}%) | "
                    f"Disco C: {specs.get('disco_livre_gb', 'N/D')} GB livres\n"
                    f"Limite IA local: {self.cpu_cores_entry.get() or 'auto'} nucleos | "
                    f"RAM maxima: {self.cpu_ram_entry.get() or '80'}%")
            self.frame.after(0, lambda: self.resources_label.configure(text=text, fg=Theme.TEXT))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def refresh_storage(self) -> None:
        from app.market_store import get_market_db_path
        from app.utils.paths import get_data_dir
        data_dir = get_data_dir()
        database = get_market_db_path()
        usage = shutil.disk_usage(data_dir)
        db_size = database.stat().st_size / (1024 * 1024) if database.exists() else 0.0
        text = (f"Dados locais: {data_dir}\nSQLite de mercado: {db_size:.2f} MB | "
                f"Disco livre: {usage.free / (1024 ** 3):.1f} GB | Retencao de ticks: 7 dias")
        self.storage_label.configure(text=text, fg=Theme.TEXT)

    def apply_desk_profile(self) -> None:
        profiles = {
            "Conservador": ("normal", "todos", "auto", 65.0),
            "Equilibrado": ("normal", "todos", "auto", 75.0),
            "Baixa latencia": ("alta", "todos", "auto", 75.0),
        }
        priority, affinity, cores, ram_pct = profiles[self.desk_profile_var.get()]
        self.cpu_priority_var.set(priority)
        self.cpu_affinity_var.set(affinity)
        self.cpu_cores_entry.delete(0, "end")
        self.cpu_cores_entry.insert(0, cores)
        self.cpu_ram_entry.delete(0, "end")
        self.cpu_ram_entry.insert(0, str(int(ram_pct)))
        c = get_config()
        c.set("cpu", "desk_profile", value=self.desk_profile_var.get())
        self.apply_cpu()

    def apply_cpu(self) -> None:
        """Aplica prioridade, afinidade e limites de recursos imediatamente."""
        from app.cpu import (apply_model_limits, memory_info, model_max_ram_mb,
                             model_n_jobs, parse_affinity, set_affinity,
                             set_priority, temperature_c)  # noqa: PLC0415
        c = get_config()
        c.set("cpu", "priority", value=self.cpu_priority_var.get())
        c.set("cpu", "affinity", value=self._affinity_value())
        c.set("cpu", "model_cores", value=self.cpu_cores_entry.get().strip() or "auto")
        try:
            c.set("cpu", "max_ram_pct", value=float(self.cpu_ram_entry.get()))
        except ValueError:
            pass
        ok_p = set_priority(self.cpu_priority_var.get())
        mask = parse_affinity(self._affinity_value())
        ok_a = bool(mask) and set_affinity(mask)
        n_jobs, max_ram = apply_model_limits(c)
        mem = memory_info()
        temp = temperature_c()
        msg = f"Prioridade {'OK' if ok_p else 'FALHOU'} | afinidade {'OK' if ok_a else 'FALHOU'}"
        msg += f" | modelos: {n_jobs} nucleo(s), RAM <= {max_ram} MB"
        msg += f" | RAM {mem.get('usage_pct', 0):.0f}% | Temp {'%.1f' % temp + 'C' if temp >= 0 else 'N/A'}"
        self.cpu_status_label.configure(text=msg, fg=Theme.SUCCESS if (ok_p or ok_a or n_jobs) else Theme.DANGER)
        self.on_status(msg)

    def test_models(self) -> None:
        """Testa o manifest.json da CDN Vercel (em thread, nao trava a GUI)."""
        url = self.models_url_entry.get().strip()
        if not url:
            self.models_res.configure(text="✘ URL vazia", fg=Theme.DANGER)
            return
        self.on_status("Testando manifest de modelos (Vercel)...")

        def worker() -> None:
            try:
                from app.integrations_client import models_url_test
                result = models_url_test(url)
            except Exception as e:  # noqa: BLE001
                result = {"ok": False, "message": str(e)}
            msg = str(result.get("message", ""))
            ok = bool(result.get("ok"))
            try:
                self.models_res.after(0, lambda: self.models_res.configure(
                    text=("✔ " if ok else "✘ ") + msg,
                    fg=Theme.SUCCESS if ok else Theme.DANGER))
                self.on_status(msg)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def save_models(self) -> None:
        """Salva URL base e API key dos modelos Vercel na config."""
        c = get_config()
        c.set("integrations", "models", "base_url", value=self.models_url_entry.get().strip())
        c.set("integrations", "models", "api_key", value=self.models_key_entry.get().strip())
        self.models_res.configure(text="✔ Modelos Vercel salvos", fg=Theme.SUCCESS)
        self.on_status("Modelos Vercel salvos")

    def test_mt5(self) -> None:
        if self.robot.connect():
            info = self.robot.account_info()
            if info:
                self.on_status(f"Conectado: {info['name']} | Saldo {info['balance']}")
            else:
                self.on_status("Conectado, mas sem info da conta")
        else:
            self.on_status(f"Falha conexao MT5: {self.robot.last_error}")
