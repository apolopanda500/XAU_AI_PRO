# -*- coding: utf-8 -*-
"""Aba Integracoes do app XAU_AI_PRO.

Centraliza configuracao e testes de conexao de:
GitHub, Sentry, Slack, CDN de modelos (Vercel) e MCP/Plugins/Extensoes.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from typing import Any, Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.config_manager import get_config
from app.integrations_client import (
    github_push_test,
    github_test,
    list_plugins,
    mcp_ping,
    models_url_test,
    sentry_test,
    slack_test,
)
from app import updater
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


def _entry(parent, width: int = 58, show: str = "") -> tk.Entry:
    return tk.Entry(parent, width=width, bg=Theme.PANEL, fg=Theme.TEXT,
                    insertbackground=Theme.TEXT, relief="flat",
                    highlightbackground=Theme.BORDER, highlightthickness=1, show=show)


def _result_label(parent) -> tk.Label:
    return tk.Label(parent, text="", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                    font=(Theme.FONT_FAMILY, 9), anchor="w")


class _ScrollFrame(tk.Frame):
    """Frame com scroll vertical simples (padrao Tkinter)."""

    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG)
        self.canvas = tk.Canvas(self, bg=Theme.BG, highlightthickness=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=Theme.BG)
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        # Scroll com a roda do mouse
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _on_wheel(self, event) -> None:
        try:
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        except Exception:  # noqa: BLE001
            pass


class IntegrationsTab:
    def __init__(self, parent: tk.Widget, robot: MT5Robot, market: MarketData,
                 on_status: Callable[[str], None]) -> None:
        self.parent = parent
        self.robot = robot
        self.market = market
        self.on_status = on_status
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Integracoes", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Repositorio, GitHub, MCP, plugins e conexoes",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)

        scroll = _ScrollFrame(self.frame)
        scroll.pack(fill="both", expand=True)
        body = scroll.inner

        # Mapeia chave -> label de resultado (usado pelos testes async)
        self._widgets: dict[str, tk.Label] = {}

        c = get_config()
        self.github_url = self._card_github(body, c.get("integrations", "github", "repo_url", default=""),
                                            c.get("integrations", "github", "token", default=""))
        self.sentry_dsn = self._card_sentry(body, c.get("integrations", "sentry", "dsn", default=""))
        self.slack_hook = self._card_slack(body, c.get("integrations", "slack", "webhook", default=""))
        self.models_url = self._card_models(body, c.get("integrations", "models", "base_url", default=""))
        self._card_mcp(body,
                       c.get("integrations", "mcp", "endpoint", default=""),
                       c.get("integrations", "plugins_dir", default="plugins"))

        self._widgets = {
            "github": self.github_url["result"],
            "sentry": self.sentry_dsn["result"],
            "slack": self.slack_hook["result"],
            "models": self.models_url["result"],
            "mcp": self.res_mcp,
        }

        self._card_updates(body)

        btns = tk.Frame(body, bg=Theme.BG)
        btns.pack(fill="x", padx=24, pady=(4, 24))
        PrimaryButton(btns, text="Salvar Integracoes", command=self.save, width=20).pack(side="left", padx=4)

    # ------------------------------------------------------------------
    def _card_updates(self, body) -> None:
        """Card de auto-atualizacao do aplicativo (GitHub Releases)."""
        card = Card(body, title="Atualizacoes do Aplicativo (ciclo mensal v1.3.x)")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        local = updater.local_version()
        self.lbl_local = tk.Label(form, text=f"Versao instalada: v{local}",
                                  bg=Theme.CARD, fg=Theme.TEXT,
                                  font=(Theme.FONT_FAMILY, 10, "bold"))
        self.lbl_local.grid(row=0, column=0, columnspan=2, sticky="w", padx=4, pady=3)
        self.res_update = _result_label(form)
        self.res_update.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        self.lbl_progress = tk.Label(form, text="", bg=Theme.CARD, fg=Theme.PRIMARY,
                                     font=(Theme.FONT_MONO, 9))
        self.lbl_progress.grid(row=2, column=0, columnspan=2, sticky="w", padx=4)
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Verificar atualizacao", command=self.do_check_update, width=20).pack(side="left", padx=4)
        self.btn_install = SecondaryButton(row, text="Baixar e instalar", command=self.do_install_update, width=20)
        self.btn_install.pack(side="left", padx=4)
        self.btn_install.configure(state="disabled")
        self._update_asset: dict | None = None

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------
    def _card_github(self, body, url: str, token: str) -> dict[str, tk.Entry]:
        card = Card(body, title="GitHub - Repositorio")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Repositorio", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_url = _entry(form, width=62)
        e_url.insert(0, url)
        e_url.grid(row=0, column=1, padx=4, pady=3)
        tk.Label(form, text="Token (opcional)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        e_tok = _entry(form, width=62, show="*")
        e_tok.insert(0, token)
        e_tok.grid(row=1, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Testar conexao", command=self.test_github, width=16).pack(side="left", padx=4)
        SecondaryButton(row, text="Status de push", command=self.test_github_push, width=16).pack(side="left", padx=4)
        return {"url": e_url, "token": e_tok, "result": res}

    def _card_sentry(self, body, dsn: str) -> dict[str, tk.Entry]:
        card = Card(body, title="Sentry - Monitoramento de erros")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="DSN", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_dsn = _entry(form, width=62)
        e_dsn.insert(0, dsn)
        e_dsn.grid(row=0, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Enviar evento teste", command=self.test_sentry, width=18).pack(side="left", padx=4)
        return {"dsn": e_dsn, "result": res}

    def _card_slack(self, body, webhook: str) -> dict[str, tk.Entry]:
        card = Card(body, title="Slack - Notificacoes (webhook)")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Webhook URL", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_hook = _entry(form, width=62)
        e_hook.insert(0, webhook)
        e_hook.grid(row=0, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Enviar mensagem teste", command=self.test_slack, width=20).pack(side="left", padx=4)
        return {"webhook": e_hook, "result": res}

    def _card_models(self, body, base_url: str) -> dict[str, tk.Entry]:
        card = Card(body, title="Modelos IA - CDN (Vercel) / download sob demanda")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="URL base", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_url = _entry(form, width=62)
        e_url.insert(0, base_url)
        e_url.grid(row=0, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Testar manifest", command=self.test_models, width=18).pack(side="left", padx=4)
        return {"base_url": e_url, "result": res}

    def _card_mcp(self, body, endpoint: str, plugins_dir: str) -> None:
        card = Card(body, title="MCP / Plugins / Extensoes")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Endpoint MCP", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        self.e_mcp = _entry(form, width=44)
        self.e_mcp.insert(0, endpoint)
        self.e_mcp.grid(row=0, column=1, padx=4, pady=3)
        tk.Label(form, text="Pasta plugins", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        self.e_plug = _entry(form, width=44)
        self.e_plug.insert(0, plugins_dir)
        self.e_plug.grid(row=1, column=1, padx=4, pady=3)
        self.res_mcp = _result_label(form)
        self.res_mcp.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        self.plugins_text = tk.Text(card.body, height=6, bg=Theme.PANEL, fg=Theme.TEXT,
                                    font=(Theme.FONT_MONO, 9), relief="flat", wrap="none")
        self.plugins_text.pack(fill="x", padx=8, pady=6)
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Ping endpoint", command=self.test_mcp, width=16).pack(side="left", padx=4)
        SecondaryButton(row, text="Atualizar lista de plugins", command=self.refresh_plugins, width=24).pack(side="left", padx=4)
        self.refresh_plugins()

    # ------------------------------------------------------------------
    # Helpers de teste (todas em thread; resultado via root.after)
    # ------------------------------------------------------------------
    def _run_async(self, fn: Callable[[], Any], widget_key: str) -> None:
        def worker() -> None:
            result = fn()
            widget = self._widgets.get(widget_key)
            if widget is not None:
                try:
                    widget.after(0, lambda: self._set_result(widget_key, result))
                    return
                except Exception:  # noqa: BLE001
                    pass
            self._set_result(widget_key, result)
        threading.Thread(target=worker, daemon=True).start()

    def _set_result(self, widget_key: str, result: dict) -> None:
        widget = self._widgets.get(widget_key)
        if widget is None:
            self.on_status(str(result.get("message", "")))
            return
        ok = bool(result.get("ok"))
        msg = str(result.get("message", ""))
        widget.configure(text=("✔ " if ok else "✘ ") + msg,
                         fg=(Theme.SUCCESS if ok else Theme.DANGER))
        self.on_status(msg)

    def _get(self, d: dict, key: str) -> str:
        w = d.get(key)
        return w.get("1.0", "end").strip() if isinstance(w, tk.Text) else (w.get().strip() if w else "")

    # ------------------------------------------------------------------
    # Acoes dos botoes
    # ------------------------------------------------------------------
    def test_github(self) -> None:
        url = self._get(self.github_url, "url")
        tok = self._get(self.github_url, "token")
        self.on_status("Testando conexao com o GitHub...")
        self._run_async(lambda: github_test(url, tok), "github")

    def test_github_push(self) -> None:
        tok = self._get(self.github_url, "token")
        self._run_async(lambda: github_push_test("", tok), "github")

    def test_sentry(self) -> None:
        dsn = self._get(self.sentry_dsn, "dsn")
        self.on_status("Enviando evento de teste ao Sentry...")
        self._run_async(lambda: sentry_test(dsn), "sentry")

    def test_slack(self) -> None:
        hook = self._get(self.slack_hook, "webhook")
        self.on_status("Enviando mensagem de teste ao Slack...")
        self._run_async(lambda: slack_test(hook), "slack")

    def test_models(self) -> None:
        url = self._get(self.models_url, "base_url")
        self.on_status("Consultando manifest de modelos...")
        self._run_async(lambda: models_url_test(url), "models")

    def test_mcp(self) -> None:
        endpoint = self.e_mcp.get().strip()
        self.on_status("Testando endpoint MCP...")
        self._run_async(lambda: mcp_ping(endpoint), "mcp")

    def refresh_plugins(self) -> None:
        self.plugins_text.delete("1.0", "end")
        try:
            items = list_plugins(self.e_plug.get().strip() or "plugins")
            if not items:
                self.plugins_text.insert("1.0", "Nenhum plugin/extension encontrado na pasta.")
                self.res_mcp.configure(text=f"0 plugins em {self.e_plug.get().strip() or 'plugins'}",
                                       fg=Theme.TEXT_SECONDARY)
                return
            lines = []
            for it in items:
                size_kb = it["size"] / 1024.0
                lines.append(f"{it['type']:5} {size_kb:8.1f} KB  {it['file']}")
            self.plugins_text.insert("1.0", "\n".join(lines))
            self.res_mcp.configure(text=f"{len(items)} item(s) detectado(s)",
                                   fg=Theme.SUCCESS)
        except Exception as e:  # noqa: BLE001
            self.plugins_text.insert("1.0", f"Erro: {e}")

    # ------------------------------------------------------------------
    # Auto-atualizacao
    # ------------------------------------------------------------------
    def do_check_update(self) -> None:
        self.res_update.configure(text="Consultando GitHub Releases...", fg=Theme.TEXT_SECONDARY)
        self.on_status("Verificando atualizacoes...")

        def worker() -> None:
            r = updater.check_update()
            def ui() -> None:
                if not r.get("ok"):
                    self.res_update.configure(text=f"✘ {r.get('error','')}", fg=Theme.DANGER)
                    return
                self._update_asset = r.get("asset")
                if r.get("has_update") and self._update_asset:
                    size_mb = self._update_asset.get("size", 0) / 1e6
                    self.res_update.configure(
                        text=f"✔ Nova versao disponivel: v{r['remote']} (atual v{r['local']}) | Setup {size_mb:.0f} MB",
                        fg=Theme.SUCCESS)
                    self.btn_install.configure(state="normal")
                    self.on_status(f"Atualizacao v{r['remote']} disponivel")
                else:
                    self.res_update.configure(
                        text=f"✔ Voce esta na versao mais recente (v{r['local']})", fg=Theme.SUCCESS)
                    self.btn_install.configure(state="disabled")
            self.frame.after(0, ui)
        threading.Thread(target=worker, daemon=True).start()

    def do_install_update(self) -> None:
        if not self._update_asset:
            return
        url = self._update_asset.get("url", "")
        if not url:
            return
        self.btn_install.configure(state="disabled")
        size_total = self._update_asset.get("size", 0)
        tmp = updater.Path(os.environ.get("TEMP", str(updater.Path.home()))) / "XAU_AI_PRO_Setup.exe"

        def progress(done: int, total: int) -> None:
            if total > 0:
                pct = done * 100 // total
                mb = done / 1e6
                self.frame.after(0, lambda: self.lbl_progress.configure(
                    text=f"Baixando... {pct:3d}%  ({mb:.1f} MB)"))

        def worker() -> None:
            r = updater.download_asset(url, tmp, progress)
            def ui() -> None:
                if not r.get("ok"):
                    self.res_update.configure(text=f"✘ {r.get('error','')}", fg=Theme.DANGER)
                    self.lbl_progress.configure(text="")
                    self.btn_install.configure(state="normal")
                    return
                self.lbl_progress.configure(text="")
                self.res_update.configure(text="✔ Download concluido. Iniciando instalador...", fg=Theme.SUCCESS)
                self.on_status("Instalador da atualizacao iniciado")
                inst = updater.install_update(tmp)
                if not inst.get("ok"):
                    self.res_update.configure(text=f"✘ {inst.get('error','')}", fg=Theme.DANGER)
            self.frame.after(0, ui)
        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def save(self) -> None:
        c = get_config()
        c.set("integrations", "github", "repo_url", value=self._get(self.github_url, "url"))
        c.set("integrations", "github", "token", value=self._get(self.github_url, "token"))
        c.set("integrations", "sentry", "dsn", value=self._get(self.sentry_dsn, "dsn"))
        c.set("integrations", "slack", "webhook", value=self._get(self.slack_hook, "webhook"))
        c.set("integrations", "models", "base_url", value=self._get(self.models_url, "base_url"))
        c.set("integrations", "mcp", "endpoint", value=self.e_mcp.get().strip())
        c.set("integrations", "plugins_dir", value=self.e_plug.get().strip() or "plugins")
        self.on_status("Integracoes salvas")