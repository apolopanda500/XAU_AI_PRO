# -*- coding: utf-8 -*-
"""Aba Integracoes do app XAU_AI_PRO.

Centraliza configuracao e testes de conexao de:
GitHub, Sentry, Slack, CDN de modelos (Vercel) e MCP/Plugins/Extensoes.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from typing import Any, Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.config_manager import get_config
from app.integrations_client import (
    figma_test,
    gitlab_test,
    github_push_test,
    github_test,
    list_plugins,
    mcp_ping,
    load_mcp_servers, mcp_server_ping,
    models_url_test,
    sentry_test,
    slack_test,
    instalados,
    catalogo,
    mcp_pesquisar,
)
from app import updater
from app.deploy_vercel import get_deploy_hook, trigger_deploy
from app.market_data import MarketData
from app.mt5_robot import MT5Robot
from app.theme.mexc import Theme


ROOT = Path(__file__).resolve().parent.parent


def _entry(parent, width: int = 58, show: str = "") -> tk.Entry:
    return tk.Entry(parent, width=width, bg=Theme.PANEL, fg=Theme.TEXT,
                    insertbackground=Theme.TEXT, relief="flat",
                    highlightbackground=Theme.BORDER, highlightthickness=1, show=show)


def _result_label(parent) -> tk.Label:
    return tk.Label(parent, text="", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                    font=(Theme.FONT_FAMILY, 9), anchor="w")


class _ScrollFrame(tk.Frame):
    """Conteudo da aba; a rolagem e controlada pelo contêiner principal."""

    def __init__(self, parent):
        super().__init__(parent, bg=Theme.BG)
        self.inner = tk.Frame(self, bg=Theme.BG)
        self.inner.pack(fill="both", expand=True)


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
        from app.components.banner import TabBanner
        TabBanner(self.frame, "integrations")
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
        self.gitlab_cfg = self._card_gitlab(
            body,
            c.get("integrations", "gitlab", "base_url", default="https://gitlab.com"),
            c.get("integrations", "gitlab", "project_path", default=""),
            c.get("integrations", "gitlab", "token", default=""),
        )
        self.figma_cfg = self._card_figma(
            body,
            c.get("integrations", "figma", "token", default=""),
            c.get("integrations", "figma", "file_key", default=""),
        )
        self.sentry_dsn = self._card_sentry(body, c.get("integrations", "sentry", "dsn", default=""))
        self.slack_hook = self._card_slack(body, c.get("integrations", "slack", "webhook", default=""))
        self.models_url = self._card_models(body, c.get("integrations", "models", "base_url", default=""))

        self._widgets = {
            "github": self.github_url["result"],
            "gitlab": self.gitlab_cfg["result"],
            "figma": self.figma_cfg["result"],
            "sentry": self.sentry_dsn["result"],
            "slack": self.slack_hook["result"],
            "models": self.models_url["result"],
        }

        self._card_mcp_servers(body)

        btns = tk.Frame(body, bg=Theme.BG)
        btns.pack(fill="x", padx=24, pady=(4, 24))
        PrimaryButton(btns, text="Salvar Integracoes", command=self.save, width=20).pack(side="left", padx=4)



    # ------------------------------------------------------------------
    def _card_mcp_servers(self, body) -> None:
        """Mostra somente os conectores operacionais aprovados para o desk."""
        card = Card(body, title="Conectores operacionais")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        self.mcp_servers = load_mcp_servers()
        # O TradingView é público e deve ficar ativo por padrão para que a
        # aba Mercado/Pesquisa consiga exibir cotações imediatamente.
        if "tradingview" in self.mcp_servers and not self.mcp_servers["tradingview"].get("enabled"):
            self.mcp_servers["tradingview"]["enabled"] = True
        self.mcp_server_entries = {}
        row = 0
        for sid, server in self.mcp_servers.items():
            lbl = tk.Label(form, text=server["name"], bg=Theme.CARD, fg=Theme.TEXT,
                           font=(Theme.FONT_FAMILY, 9, "bold"))
            lbl.grid(row=row, column=0, sticky="w", padx=4, pady=3)
            tk.Label(form, text=server["description"], bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                     font=(Theme.FONT_FAMILY, 8)).grid(row=row + 1, column=0, columnspan=2,
                                                       sticky="w", padx=4, pady=(0, 2))
            e_end = _entry(form, width=46)
            e_end.insert(0, server["endpoint"])
            e_end.grid(row=row, column=2, columnspan=2, padx=4, pady=3)
            e_key = _entry(form, width=20, show="*")
            e_key.insert(0, server["api_key"])
            e_key.grid(row=row + 1, column=2, columnspan=2, padx=4, pady=(0, 2))
            # Campo DATABASE_URL extra apenas para o Postgres/SQLite
            e_db = None
            if sid == "postgres_sqlite":
                e_db = _entry(form, width=46)
                e_db.insert(0, server.get("database_url", ""))
                e_db.grid(row=row + 2, column=2, columnspan=2, padx=4, pady=(0, 2))
                tk.Label(form, text="DATABASE_URL", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY,
                         font=(Theme.FONT_FAMILY, 8)).grid(row=row + 2, column=0, columnspan=2, sticky="w", padx=4)
            var = tk.BooleanVar(value=server["enabled"])
            tk.Checkbutton(form, text="Ativo", variable=var, bg=Theme.CARD,
                           fg=Theme.TEXT_SECONDARY, selectcolor=Theme.PANEL,
                           activebackground=Theme.CARD, font=(Theme.FONT_FAMILY, 8)).grid(
                row=row, column=4, sticky="w", padx=4, pady=3)
            res = _result_label(form)
            res.grid(row=row + 1, column=3, columnspan=2, sticky="w", padx=4, pady=(0, 2))
            self.mcp_server_entries[sid] = {"endpoint": e_end, "api_key": e_key,
                                            "enabled": var, "result": res}
            if e_db is not None:
                self.mcp_server_entries[sid]["database_url"] = e_db
            row += 2
        # Botoes de acao
        row_btns = tk.Frame(card.body, bg=Theme.CARD)
        row_btns.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row_btns, text="Testar todos", command=self.test_mcp_servers, width=16).pack(side="left", padx=4)
        SecondaryButton(row_btns, text="Salvar MCP Servers", command=self.save_mcp_servers, width=20).pack(side="left", padx=4)

    def test_mcp_servers(self) -> None:
        for sid, widgets in self.mcp_server_entries.items():
            server = self.mcp_servers.get(sid, {})
            extra = {"database_url": ""}
            if "database_url" in widgets:
                extra["database_url"] = widgets["database_url"].get().strip()
            server = dict(server, endpoint=widgets["endpoint"].get().strip(),
                          api_key=widgets["api_key"].get().strip(),
                          enabled=widgets["enabled"].get(), **extra)
            server_id = sid

            def worker(srv: dict[str, Any], sid: str) -> None:
                result = mcp_server_ping(srv)
                w = self.mcp_server_entries.get(sid)
                if w is not None:
                    try:
                        w["result"].after(0, lambda r=result, sid=sid: self._apply_mcp_result(sid, r))
                        return
                    except Exception:  # noqa: BLE001
                        pass
                self._apply_mcp_result(sid, result)

            threading.Thread(target=worker, args=(server, server_id), daemon=True).start()

    def _apply_mcp_result(self, sid: str, result: dict) -> None:
        w = self.mcp_server_entries.get(sid)
        if w is None:
            return
        ok = bool(result.get("ok"))
        w["result"].configure(text=("✔ " if ok else "✘ ") + str(result.get("message", "")),
                              fg=(Theme.SUCCESS if ok else Theme.DANGER))

    def save_mcp_servers(self) -> None:
        c = get_config()
        servers = {}
        for sid, widgets in self.mcp_server_entries.items():
            rec = {
                "endpoint": widgets["endpoint"].get().strip(),
                "api_key": widgets["api_key"].get().strip(),
                "enabled": widgets["enabled"].get(),
            }
            if "database_url" in widgets:
                rec["database_url"] = widgets["database_url"].get().strip()
            servers[sid] = rec
        c.set("integrations", "mcp", "servers", value=servers)
        self.mcp_servers = load_mcp_servers()
        self.on_status("MCP Servers salvos")

    def _card_mcp_marketplace(self, body) -> None:
        """Pesquisa e instala MCP servers dentro do app."""
        from app.components.cards import Card
        card = Card(body, title="MCP Marketplace (instalar novos servidores)")
        card.pack(fill="x", padx=24, pady=10)
        fm = tk.Frame(card.body, bg=Theme.CARD)
        fm.pack(fill="x", padx=8, pady=8)
        tk.Label(fm, text="Buscar MCP:", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(side="left", padx=4)
        self.mcp_search_entry = tk.Entry(fm, width=28, bg=Theme.PANEL, fg=Theme.TEXT,
                                         relief="flat", highlightbackground=Theme.BORDER,
                                         highlightthickness=1)
        self.mcp_search_entry.pack(side="left", padx=4)
        SecondaryButton(fm, text="Buscar", command=self.mcp_market_search, width=10).pack(side="left", padx=4)
        SecondaryButton(fm, text="Listar todos", command=self.mcp_market_list, width=12).pack(side="left", padx=4)
        self.mcp_market_lbl = tk.Label(card.body, text="Digite um termo e clique em Buscar (ex.: 'github', 'fetch', 'memoria').",
                                       bg=Theme.CARD, fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9),
                                       anchor="w", justify="left", wraplength=900)
        self.mcp_market_lbl.pack(fill="x", padx=8, pady=(0, 6))
        self.mcp_market_btns = tk.Frame(card.body, bg=Theme.CARD)
        self.mcp_market_btns.pack(fill="x", padx=8, pady=(0, 8))
        self._mcp_market_items = []
        tk.Label(card.body, text="Instalados: " + (", ".join(instalados()) or "nenhum"),
                 bg=Theme.CARD, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 8)).pack(fill="x", padx=8, pady=(0, 8))

    def mcp_market_search(self) -> None:
        q = self.mcp_search_entry.get().strip()
        self._mcp_market_render(mcp_pesquisar(q))

    def mcp_market_list(self) -> None:
        self._mcp_market_render(catalogo())

    def _mcp_market_render(self, items: list) -> None:
        for w in self.mcp_market_btns.winfo_children():
            w.destroy()
        self._mcp_market_items = items
        if not items:
            tk.Label(self.mcp_market_btns, text="Nenhum MCP encontrado.", bg=Theme.CARD,
                     fg=Theme.TEXT_MUTED).pack(anchor="w")
        for it in items[:14]:
            mid = it.get("id", "")
            nome = it.get("name", mid)
            desc = it.get("desc", "")
            linha = tk.Frame(self.mcp_market_btns, bg=Theme.CARD)
            linha.pack(fill="x", pady=1)
            tk.Label(linha, text=f"{nome}  [{it.get('type')}]", bg=Theme.CARD, fg=Theme.TEXT,
                     font=(Theme.FONT_FAMILY, 9, "bold"), width=22, anchor="w").pack(side="left", padx=4)
            tk.Label(linha, text=desc, bg=Theme.CARD, fg=Theme.TEXT_MUTED,
                     font=(Theme.FONT_FAMILY, 8), anchor="w").pack(side="left", padx=4, expand=True)
            ja = mid in instalados()
            texto = "Instalar" if not ja else "Reinstalar"
            b = SecondaryButton(linha, text=texto, width=10,
                                command=lambda m=mid: self._mcp_market_install(m))
            b.pack(side="right", padx=4)
            if ja:
                b2 = SecondaryButton(linha, text="Remover", width=9,
                                     command=lambda m=mid: self._mcp_market_remove(m))
                b2.pack(side="right", padx=2)

    def _mcp_market_install(self, mid: str) -> None:
        self.on_status("Instalação de MCPs não aprovados está desativada")

    def _mcp_market_remove(self, mid: str) -> None:
        self.on_status("Remoção é gerenciada pelo catálogo operacional")

    # ------------------------------------------------------------------
    # Deploy Vercel
    # ------------------------------------------------------------------
    def _card_vercel_deploy(self, body) -> None:
        """Card para disparar deploy automatico do backend via Vercel Deploy Hook."""
        card = Card(body, title="Deploy Vercel (backend)")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)

        tk.Label(form, text="Deploy Hook URL:", bg=Theme.CARD, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 10)).grid(row=0, column=0, sticky="w", pady=4)
        self.e_vercel_hook = _entry(form, width=72)
        self.e_vercel_hook.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        self.e_vercel_hook.insert(0, get_deploy_hook())
        form.grid_columnconfigure(1, weight=1)

        info = tk.Label(form, text="Cole a URL do Deploy Hook do projeto Vercel. "
                                    "O deploy e iniciado automaticamente via POST, sem necessidade de login.",
                        bg=Theme.CARD, fg=Theme.TEXT_SECONDARY, font=(Theme.FONT_FAMILY, 9), justify="left")
        info.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 8))

        row2 = tk.Frame(form, bg=Theme.CARD)
        row2.grid(row=2, column=0, columnspan=2, sticky="w")
        PrimaryButton(row2, text="Deploy Agora", command=self._do_vercel_deploy, width=16).pack(side="left", padx=(0, 8))
        SecondaryButton(row2, text="Ver Status", command=self._check_vercel_deploy, width=14).pack(side="left", padx=(0, 8))

        self.res_vercel_deploy = _result_label(form)
        self.res_vercel_deploy.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def _do_vercel_deploy(self) -> None:
        url = self.e_vercel_hook.get().strip()
        self.res_vercel_deploy.config(text="Iniciando deploy...", fg=Theme.TEXT)
        self.on_status("Deploy Vercel em andamento...")

        def worker() -> None:
            r = trigger_deploy(hook_url=url)
            self.frame.after(0, lambda: self._show_vercel_result(r))
        threading.Thread(target=worker, daemon=True).start()

    def _check_vercel_deploy(self) -> None:
        self.res_vercel_deploy.config(text="Consultando status...", fg=Theme.TEXT)

        def worker() -> None:
            from app.deploy_vercel import check_status
            r = check_status(job_id="")
            self.frame.after(0, lambda: self._show_vercel_result(r))
        threading.Thread(target=worker, daemon=True).start()

    def _show_vercel_result(self, r: dict[str, Any]) -> None:
        color = Theme.SUCCESS if r.get("ok") else Theme.DANGER
        self.res_vercel_deploy.config(text=r.get("message", ""), fg=color)
        self.on_status(r.get("message", ""))

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

    def _card_gitlab(self, body, base_url: str, project_path: str, token: str) -> dict[str, tk.Entry]:
        card = Card(body, title="GitLab - Repositorio")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="URL GitLab", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_url = _entry(form, width=62)
        e_url.insert(0, base_url)
        e_url.grid(row=0, column=1, padx=4, pady=3)
        tk.Label(form, text="Projeto (grupo/repo)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        e_project = _entry(form, width=62)
        e_project.insert(0, project_path)
        e_project.grid(row=1, column=1, padx=4, pady=3)
        tk.Label(form, text="Token (opcional)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=2, column=0, sticky="w", padx=4)
        e_tok = _entry(form, width=62, show="*")
        e_tok.insert(0, token)
        e_tok.grid(row=2, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=3, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Testar GitLab", command=self.test_gitlab, width=16).pack(side="left", padx=4)
        return {"url": e_url, "project": e_project, "token": e_tok, "result": res}

    def _card_figma(self, body, token: str, file_key: str) -> dict[str, tk.Entry]:
        card = Card(body, title="Figma - Design")
        card.pack(fill="x", padx=24, pady=10)
        form = tk.Frame(card.body, bg=Theme.CARD)
        form.pack(fill="x", padx=8, pady=8)
        tk.Label(form, text="Token", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=4)
        e_tok = _entry(form, width=62, show="*")
        e_tok.insert(0, token)
        e_tok.grid(row=0, column=1, padx=4, pady=3)
        tk.Label(form, text="File Key (opcional)", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).grid(row=1, column=0, sticky="w", padx=4)
        e_file = _entry(form, width=62)
        e_file.insert(0, file_key)
        e_file.grid(row=1, column=1, padx=4, pady=3)
        res = _result_label(form)
        res.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))
        row = tk.Frame(card.body, bg=Theme.CARD)
        row.pack(fill="x", padx=8, pady=(0, 8))
        SecondaryButton(row, text="Testar Figma", command=self.test_figma, width=16).pack(side="left", padx=4)
        SecondaryButton(row, text="Abrir projeto", command=self.open_figma, width=16).pack(side="left", padx=4)
        return {"token": e_tok, "file_key": e_file, "result": res}

    def open_figma(self) -> None:
        file_key = self._get(self.figma_cfg, "file_key")
        if not file_key:
            self.figma_cfg["result"].configure(text="✘ Informe ou vincule um File Key", fg=Theme.DANGER)
            return
        webbrowser.open(f"https://www.figma.com/design/{file_key}")
        self.figma_cfg["result"].configure(text="✔ Projeto Figma aberto", fg=Theme.SUCCESS)

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

    def test_gitlab(self) -> None:
        url = self._get(self.gitlab_cfg, "url")
        project = self._get(self.gitlab_cfg, "project")
        tok = self._get(self.gitlab_cfg, "token")
        self.on_status("Testando conexao com o GitLab...")
        self._run_async(lambda: gitlab_test(url, tok, project), "gitlab")

    def test_figma(self) -> None:
        tok = self._get(self.figma_cfg, "token")
        file_key = self._get(self.figma_cfg, "file_key")
        self.on_status("Testando conexao com o Figma...")
        self._run_async(lambda: figma_test(tok, file_key), "figma")

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
    def _save_deploy_hook_env(self, url: str) -> None:
        """Atualiza VERCEL_DEPLOY_HOOK_URL no .env.local, se possivel."""
        try:
            env_path = ROOT / ".env.local"
            lines = []
            found = False
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("VERCEL_DEPLOY_HOOK_URL="):
                        lines.append(f"VERCEL_DEPLOY_HOOK_URL={url}")
                        found = True
                    else:
                        lines.append(line)
            if not found:
                lines.append(f"VERCEL_DEPLOY_HOOK_URL={url}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

    def save(self) -> None:
        c = get_config()
        c.set("integrations", "github", "repo_url", value=self._get(self.github_url, "url"))
        c.set("integrations", "github", "token", value=self._get(self.github_url, "token"))
        c.set("integrations", "gitlab", "base_url", value=self._get(self.gitlab_cfg, "url"))
        c.set("integrations", "gitlab", "project_path", value=self._get(self.gitlab_cfg, "project"))
        c.set("integrations", "gitlab", "token", value=self._get(self.gitlab_cfg, "token"))
        c.set("integrations", "figma", "token", value=self._get(self.figma_cfg, "token"))
        c.set("integrations", "figma", "file_key", value=self._get(self.figma_cfg, "file_key"))
        c.set("integrations", "sentry", "dsn", value=self._get(self.sentry_dsn, "dsn"))
        c.set("integrations", "slack", "webhook", value=self._get(self.slack_hook, "webhook"))
        c.set("integrations", "models", "base_url", value=self._get(self.models_url, "base_url"))
        servers = {}
        for sid, widgets in self.mcp_server_entries.items():
            servers[sid] = {
                "endpoint": widgets["endpoint"].get().strip(),
                "api_key": widgets["api_key"].get().strip(),
                "enabled": widgets["enabled"].get(),
            }
        c.set("integrations", "mcp", "servers", value=servers)
        self.on_status("Integracoes salvas")
        self.on_status("Integracoes salvas")
