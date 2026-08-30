"""
XAU AI PRO - GUI (Desktop)
Interface grafica moderna com:
  - Tela de Login (usuario/senha, usuario padrao admin/admin)
  - Abas:
      1. Dashboard        (conta, estado MT5/IA, P&L)
      2. Mercado Tempo Real (cotacoes ao vivo via MT5 / yfinance)
      3. Predicoes        (lista prediction_*.json)
      4. MT5 / Robo       (conexao MT5, ordens, posicoes, historico)
      5. API / Conexoes   (configurar API keys, testar servicos)
      6. Treinamento      (treinar, predizer, auto-approve)
      7. Assistente IA    (chat com memoria)
      8. Ferramentas      (lot, relojo, calendario)
      9. Integracoes      (GitHub, Figma, Brave)
     10. Memoria           (pensamentos, notas diarias)
     11. Configuracoes    (ativos, timeframe, tema)

Tecnologia: Tkinter (stdlib) + threads para nao travar a UI.
"""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Adaptacao de import quando rodando como app ou modulo
try:
    import config_store as cs
    import market_live as ml
    import mt5_integration as mi
    import themes
    import wallpaper
    import assistant
    import daily_tools
    import integrations
    import design_system as ds
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import config_store as cs
    import market_live as ml
    import mt5_integration as mi
    import themes
    import wallpaper
    import assistant
    import daily_tools
    import integrations
    import design_system as ds


# Garante criar usuario admin/admin e schema do DB na primeira execucao
try:
    cs.ensure_default_user()
    cs.ensure_schema()
except Exception:
    pass


ROOT = Path(__file__).resolve().parent.parent
PY_DIR = ROOT / "Python"
MQL_DATA = ROOT / "MQL5" / "Files" / "Data"
REPORTS_DIR = ROOT / "Reports"

SYMBOLS_DEFAULT = [
    "XAUUSD", "XAUUSDc", "BTCUSD", "ETHUSD", "EURUSD",
    "GBPUSD", "USDJPY", "AUDUSD", "SPX500", "US30",
]

# ============================================================
# HELPERS DE SERVIÇOS
# ============================================================
def _py() -> str:
    import sys as _s

    return _s.executable or "python"


def is_port_open(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", int(port))) == 0


def start_backend(port: int) -> subprocess.Popen | None:
    api = PY_DIR / "backend" / "api.py"
    if not api.exists():
        return None
    log = ROOT / "Logs" / "backend.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    f = open(log, "a", encoding="utf-8")
    return subprocess.Popen(
        [_py(), str(api)],
        stdout=f,
        stderr=f,
        cwd=str(PY_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def start_dashboard(port: int) -> subprocess.Popen | None:
    if not (PY_DIR / "dashboard" / "app.py").exists():
        return None
    log = ROOT / "Logs" / "dashboard.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    f = open(log, "a", encoding="utf-8")
    return subprocess.Popen(
        [_py(), "-m", "streamlit", "run", str(PY_DIR / "dashboard" / "app.py"),
         "--server.port", str(port), "--server.headless", "true"],
        stdout=f,
        stderr=f,
        cwd=str(PY_DIR),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
# ============================================================
# APLICACAO PRINCIPAL
# ============================================================
class XauAiProApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.market = ml.MarketLive()
        self.assistant = assistant.AIAssistant()
        self.msg_queue: queue.Queue = queue.Queue()
        self._procs: list[subprocess.Popen] = []
        self._live_running = False
        self._quote_rows: dict[str, list] = {}
        self._theme = cs.get_theme()
        self._wallpaper: wallpaper.CryptoWallpaper | None = None
        self.current_theme = self._theme
        self.colors = ds.get_colors(self.current_theme)

        root.title("XAU AI PRO — Trading Desk")
        root.geometry("1100x720")
        root.minsize(920, 640)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Barra de status inferior
        self.status_var = tk.StringVar(value="Pronto. Faça login para continuar.")
        self._build_status_bar()

        # Slack watcher: eventos do EA -> Slack em tempo real (thread daemon)
        try:
            import slack_watcher
            slack_watcher.start_watcher(interval=10.0)
        except Exception:
            pass

        # Estado da sessão
        cs.ensure_default_user()
        cs.ensure_schema()

        # Aplica tema salvo
        self.apply_theme(self._theme)

        # Inicia na tela de login (ou auto-login se "lembrar")
        # Auto-login sempre garantido: garante admin e abre direto nas abas
        try:
            cs.ensure_default_user()
            cs.set_session("admin")
        except Exception:
            pass

        # Sentry: atribui usuario corrente (coluna User em Conversas)
        try:
            import sys as _sys
            _PY = Path(__file__).resolve().parent.parent / "Python"
            if str(_PY) not in _sys.path:
                _sys.path.insert(0, str(_PY))
            from sentry_config import set_current_user
            set_current_user("admin", username="admin")
        except Exception:
            pass
        self.show_login()
        self.root.after(300, self._auto_login)

        # Processador de mensagens da fila (threads -> UI)
        root.after(120, self._drain_queue)

    def _auto_login(self) -> None:
        user = cs.get_session()
        if user:
            cs.set_session(user)
            self.set_status(f"Sessão automática: {user}")
            self.show_main()

    # ----------------------------------------------------------
    # TEMA
    # ----------------------------------------------------------
    def apply_theme(self, theme: str) -> None:
        """Aplica um dos temas disponiveis a toda a interface."""
        self._theme = theme if theme in themes.list_themes() else "dark"
        self.current_theme = self._theme
        self.colors = ds.get_colors(self.current_theme)
        t = themes.apply_ttk_theme(ttk.Style(), self._theme)
        self._theme_colors = t
        self.root.configure(background=t["bg"])
        # Reaplica se houver wallpaper ativo
        if self._wallpaper is not None:
            self._wallpaper.theme = t
            self._wallpaper.configure(bg=t["bg"])

    def _apply_theme_from_cfg(self) -> None:
        """Aplica o tema selecionado na aba Configuracoes."""
        theme = self.cfg_theme.get() if hasattr(self, "cfg_theme") else cs.get_theme()
        self.apply_theme(theme)
        cs.set_theme(theme)
        self.set_status(f"Tema alterado para: {theme}")
    # ----------------------------------------------------------
    def _build_status_bar(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(side="bottom", fill="x")
        ttk.Label(bar, textvariable=self.status_var, anchor="w",
                  relief="sunken", padding=(6, 3)).pack(fill="x")
        self.statusbar_widget = bar

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _on_close(self) -> None:
        """Encerra animacoes e processos ao fechar a janela."""
        self._live_running = False
        if self._wallpaper is not None:
            self._wallpaper.stop()
            self._wallpaper = None
        for p in self._procs:
            try:
                p.terminate()
            except Exception:
                pass
        self.root.destroy()

    # ----------------------------------------------------------
    # FILA DE THREADS -> UI
    # ----------------------------------------------------------
    def _drain_queue(self) -> None:
        try:
            while True:
                item = self.msg_queue.get_nowait()
                kind = item[0]
                if kind == "market":
                    self._update_quote_table(item[1])
                elif kind == "status":
                    self.set_status(item[1])
                elif kind == "done":
                    self._on_task_done(item[1])
                elif kind == "chat":
                    self._append_chat(f"Assistente: {item[1]}")
                    self.set_status("Resposta do assistente recebida.")
                elif kind == "github_test":
                    res = item[1]
                    self.gh_status.set("OK" if res.ok else "Falhou")
                    self._ilog(f"[GitHub] {res.message}")
                    if res.data and "repos" in res.data:
                        for r in res.data["repos"]:
                            self._ilog(f"  - {r['name']}")
                elif kind == "figma_test":
                    res = item[1]
                    self.figma_status.set("OK" if res.ok else "Falhou")
                    self._ilog(f"[Figma] {res.message}")
                elif kind == "brave_search":
                    res = item[1]
                    self.brave_status.set("OK" if res.ok else "Falhou")
                    self._ilog(f"[Brave] {res.message}")
                    if res.data:
                        for r in res.data.get("results", []):
                            self._ilog(f"  - {r}")
                elif kind == "slack_test":
                    res = item[1]
                    self.slack_status.set("OK" if res.ok else "Falhou")
                    self._ilog(f"[Slack] {res.message}")
                elif kind == "mt5_order":
                    self._mt5_log(item[1])
                    self.set_status(item[1])
                elif kind == "mt5_positions":
                    self._mt5_update_positions_table(item[1])
                    self._mt5_update_metrics()
                    self.set_status(f"{len(item[1])} posicoes abertas")
                elif kind == "mt5_history":
                    self._mt5_update_history_table(item[1])
                    self.set_status(f"{len(item[1])} deals no historico")
                elif kind == "mt5_close":
                    res = item[1]
                    msg = f"Posicao fechada: ticket {res.get('ticket')}" if res.get("ok") else f"Erro ao fechar: {res.get('error')}"
                    self._mt5_log(msg)
                    self.set_status(msg)
                    self._mt5_refresh_positions()
        except queue.Empty:
            pass
        self.root.after(120, self._drain_queue)

    def log(self, text: str) -> None:
        """Registra no-widget de logs da aba treinamento, se existir."""
        if hasattr(self, "train_log") and self.train_log is not None:
            try:
                self.train_log.configure(state="normal")
                self.train_log.insert("end", text + "\n")
                self.train_log.see("end")
                self.train_log.configure(state="disabled")
            except Exception:
                pass


    # ----------------------------------------------------------
    # TELA DE LOGIN
    # ----------------------------------------------------------
    def show_login(self) -> None:
        self._destroy_body()

        # Wallpaper animado no fundo
        ui_cfg = cs.get_ui_config()
        if ui_cfg.get("wallpaper_enabled", True):
            self._wallpaper = wallpaper.create_wallpaper(self.root, self._theme_colors)
            self._wallpaper.pack(fill="both", expand=True)
            container = self._wallpaper
        else:
            self.login_frame = ttk.Frame(self.root)
            self.login_frame.pack(fill="both", expand=True)
            container = self.login_frame

        wrap = ttk.Frame(container)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(wrap, bg=self._theme_colors["bsel"], padx=30, pady=30,
                        highlightbackground=self._theme_colors["accent"],
                        highlightthickness=2)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(card, text="XAU AI PRO", font=("Segoe UI", 24, "bold"),
                 bg=self._theme_colors["bsel"], fg=self._theme_colors["fg"]).grid(
            row=0, column=0, columnspan=2, pady=(0, 4)
        )
        tk.Label(card, text="Plataforma de Trading Quantitativo + IA",
                 bg=self._theme_colors["bsel"], fg=self._theme_colors["accent"],
                 font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=2, pady=(0, 18))

        tk.Label(card, text="Usuario:", bg=self._theme_colors["bsel"],
                 fg=self._theme_colors["fg"]).grid(row=2, column=0, sticky="e", pady=4)
        self.login_user = tk.Entry(card, bg=self._theme_colors["bg"],
                                   fg=self._theme_colors["fg"], insertbackground=self._theme_colors["fg"])
        self.login_user.grid(row=2, column=1, pady=4, padx=6)
        self.login_user.insert(0, "admin")

        tk.Label(card, text="Senha:", bg=self._theme_colors["bsel"],
                 fg=self._theme_colors["fg"]).grid(row=3, column=0, sticky="e", pady=4)
        self.login_pass = tk.Entry(card, show="*", bg=self._theme_colors["bg"],
                                   fg=self._theme_colors["fg"], insertbackground=self._theme_colors["fg"])
        self.login_pass.grid(row=3, column=1, pady=4, padx=6)
        self.login_pass.insert(0, "admin")

        # Remember me checkbox
        self.login_remember = tk.BooleanVar(value=cs.get_remember_me())
        tk.Checkbutton(card, text="Lembrar sessao", variable=self.login_remember,
                       bg=self._theme_colors["bsel"], fg=self._theme_colors["fg"],
                       selectcolor=self._theme_colors["bg"]).grid(
            row=5, column=0, columnspan=2, pady=4
        )

        btns = tk.Frame(card, bg=self._theme_colors["bsel"])
        btns.grid(row=4, column=0, columnspan=2, pady=14)
        tk.Button(btns, text="Entrar", command=self._do_login,
                  bg=self._theme_colors["accent"], fg="white",
                  activebackground=self._theme_colors["accent_hover"]).pack(side="left", padx=6)
        tk.Button(btns, text="Cadastrar", command=self._do_register,
                  bg=self._theme_colors["bsel"], fg=self._theme_colors["fg"]).pack(side="left", padx=6)

        tk.Label(card,
                  text="Padrao: admin / admin — use Cadastrar para criar novos usuarios",
                  bg=self._theme_colors["bsel"], fg="#999", font=("Segoe UI", 8)).grid(
            row=6, column=0, columnspan=2, pady=(8, 0)
        )
        self.login_pass.bind("<Return>", lambda e: self._do_login())

    def _destroy_body(self) -> None:
        for w in self.root.winfo_children():
            if w is not self.statusbar_widget:
                w.destroy()

    def _do_login(self) -> None:
        u = self.login_user.get()
        p = self.login_pass.get()
        if cs.authenticate(u, p):
            cs.set_session(u)
            if hasattr(self, "login_remember") and self.login_remember.get():
                cs.set_remember_me(True)
            self.set_status(f"Sessão iniciada: {u}")
            self.show_main()
        else:
            messagebox.showerror("Login", "Usuário ou senha inválidos.")

    def _do_register(self) -> None:
        u = self.login_user.get()
        p = self.login_pass.get()
        if not u or not p:
            messagebox.showwarning("Cadastro", "Informe usuário e senha.")
            return
        if cs.create_user(u, p):
            messagebox.showinfo("Cadastro", "Usuário criado com sucesso! Faça login.")
        else:
            messagebox.showwarning("Cadastro", "Usuário já existe.")
    # ----------------------------------------------------------
    # TELA PRINCIPAL (ABAS)
    # ----------------------------------------------------------
    def show_main(self) -> None:
        self._destroy_body()
        if self._wallpaper is not None:
            self._wallpaper.stop()
            self._wallpaper = None

        self.main = ttk.Frame(self.root)
        self.main.pack(fill="both", expand=True)

        self.nb = ttk.Notebook(self.main)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self._build_dashboard_tab()
        self._build_market_tab()
        self._build_predictions_tab()
        self._build_mt5_tab()
        self._build_api_tab()
        self._build_training_tab()
        self._build_assistant_tab()
        self._build_tools_tab()
        self._build_integrations_tab()
        self._build_memory_tab()
        self._build_config_tab()

        # Inicia atualizacao de mercado em segundo plano
        self._start_live_updates()
        # Dica do assistente na barra de status
        self.set_status(self.assistant.quick_tip())

    # ----------------------------------------------------------
    # ABA 1: DASHBOARD
    # ----------------------------------------------------------
    def _build_dashboard_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Dashboard   ")

        self.dash_text = scrolledtext.ScrolledText(
            tab, font=("Consolas", 10), state="disabled", wrap="none"
        )
        self.dash_text.pack(fill="both", expand=True, padx=8, pady=8)

        btn = ttk.Button(tab, text="Atualizar agora", command=self._refresh_dashboard)
        btn.pack(pady=(0, 8))

        self._refresh_dashboard()

    def _refresh_dashboard(self) -> None:
        lines = []
        header = "=" * 52
        lines.append(header)
        lines.append("            XAU AI PRO — DASHBOARD")
        lines.append(header)
        lines.append("Gerado em: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        lines.append("")

        cfg = cs.get_api_config()
        b_port = cfg.get("backend_port", 8000)
        d_port = cfg.get("dashboard_port", 8501)
        l_port = cfg.get("litellm_port", 4000)

        mt5 = self.market.provider_available("mt5")
        yf = self.market.provider_available("yfinance")
        backend = is_port_open(int(b_port))
        dash = is_port_open(int(d_port))
        proxy = is_port_open(int(l_port))

        lines.append(f"  MetaTrader 5 : {'ONLINE' if mt5 else 'offline'}")
        lines.append(f"  Yahoo Finance: {'ONLINE' if yf else 'offline'}")
        lines.append(f"  Backend API  : {'online  ->  http://127.0.0.1:%s' % b_port if backend else 'offline'}")
        lines.append(f"  Dashboard    : {'online  ->  http://127.0.0.1:%s' % d_port if dash else 'offline'}")
        lines.append(f"  LiteLLM Proxy: {'online' if proxy else 'offline'}")
        lines.append("")
        lines.append("  -- Conta / Banco --")

        try:
            conn = cs.db_connect()
            c = conn.cursor()
            c.execute("SELECT login,balance,equity,margin,company FROM account WHERE id=1")
            acc = c.fetchone()
            if acc:
                lines.append(f"  Login...: {acc[0]}  ({acc[4] or ''})")
                lines.append(f"  Saldo..: {acc[1]:,.2f}")
                lines.append(f"  Equity.: {acc[2]:,.2f}")
                lines.append(f"  Margem.: {acc[3]:,.2f}")
            else:
                lines.append("  (sem registro de conta ainda)")
            c.execute("SELECT COUNT(*) FROM trades")
            ntrades = c.fetchone()[0]
            conn.close()
            lines.append(f"  Trades registrados: {ntrades}")
        except Exception as e:
            lines.append(f"  erro no banco: {e}")

        lines.append("")
        lines.append(header)
        lines.append("Use a aba 'Mercado' para cotações ao vivo e 'Treinamento' para IA.")

        self.dash_text.configure(state="normal")
        self.dash_text.delete("1.0", "end")
        self.dash_text.insert("end", "\n".join(lines))
        self.dash_text.configure(state="disabled")

    # ----------------------------------------------------------
    # ABA 2: MERCADO EM TEMPO REAL
    # ----------------------------------------------------------
    def _build_market_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Mercado   ")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Símbolos (separados por vírgula):").pack(side="left")
        self.market_symbols_var = tk.StringVar(value=", ".join(SYMBOLS_DEFAULT))
        e = ttk.Entry(top, textvariable=self.market_symbols_var, width=46)
        e.pack(side="left", padx=6)
        ttk.Button(top, text="Aplicar", command=self._apply_market_symbols).pack(side="left")
        self.market_state = tk.StringVar(value="parado")
        ttk.Label(top, textvariable=self.market_state, foreground="#0a0").pack(side="left", padx=10)

        cols = ("symbol", "price", "bid", "ask", "chg", "chg%", "spread", "src", "time")
        self.market_tree = ttk.Treeview(tab, columns=cols, show="headings", height=18)
        heads = {
            "symbol": "Símbolo", "price": "Preço", "bid": "Bid", "ask": "Ask",
            "chg": "Variação", "chg%": "%", "spread": "Spread",
            "src": "Fonte", "time": "Hora",
        }
        widths = {"symbol": 90, "price": 90, "bid": 90, "ask": 90, "chg": 90,
                  "chg%": 60, "spread": 60, "src": 80, "time": 70}
        for c in cols:
            self.market_tree.heading(c, text=heads[c])
            self.market_tree.column(c, width=widths[c], anchor="center")
        vs = ttk.Scrollbar(tab, orient="vertical", command=self.market_tree.yview)
        self.market_tree.configure(yscrollcommand=vs.set)
        self.market_tree.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        vs.pack(side="right", fill="y")

        self._apply_market_symbols()

    def _apply_market_symbols(self) -> None:
        raw = self.market_symbols_var.get()
        self._symbols = [s.strip() for s in raw.replace(" ", "").split(",") if s.strip()]
        self._clear_market_rows()
        if self._live_running:
            self.market_state.set("atualizando...")

    def _clear_market_rows(self) -> None:
        for iid in self.market_tree.get_children():
            self.market_tree.delete(iid)
        self._quote_rows = {}

    def _start_live_updates(self) -> None:
        if self._live_running:
            return
        self._live_running = True
        threading.Thread(target=self._live_worker, daemon=True).start()

    def _live_worker(self) -> None:
        while self._live_running:
            cfg = cs.get_api_config()
            symbols = getattr(self, "_symbols", SYMBOLS_DEFAULT)
            if symbols:
                try:
                    quotes = self.market.get_many(symbols)
                    if quotes:
                        payload = self._prepare_quote_rows(quotes)
                        self.msg_queue.put(("market", payload))
                except Exception:
                    pass
            try:
                time.sleep(max(2, int(cfg.get("refresh_seconds", 5))))
            except Exception:
                time.sleep(5)

    def _prepare_quote_rows(self, quotes: dict) -> list:
        rows = []
        for sym, q in quotes.items():
            chg = q.get("change", 0.0)
            chgp = q.get("change_pct", 0.0)
            color = "+" if chg >= 0 else "-"
            rows.append(
                {
                    "symbol": sym,
                    "price": f"{q.get('price', 0):,.5f}",
                    "bid": f"{q.get('bid', 0):,.5f}",
                    "ask": f"{q.get('ask', 0):,.5f}",
                    "chg": f"{color}{abs(chg):.5f}",
                    "chg%": f"{chgp:+.3f}%",
                    "spread": f"{q.get('spread', 0):.1f}",
                    "src": q.get("source", "-"),
                    "time": q.get("time", "-"),
                }
            )
        return rows

    def _update_quote_table(self, rows: list) -> None:
        self._clear_market_rows()
        for r in rows:
            up = r["chg"].startswith("+")
            tag = "green" if up else ("red" if r["chg"].startswith("-") else "")
            self.market_tree.insert("", "end", values=tuple(r.values()), tags=(tag,))
        self.market_tree.tag_configure("green", foreground="#0a0")
        self.market_tree.tag_configure("red", foreground="#d00")
        self.market_state.set(f"{len(rows)} ativos ao vivo")

    # ----------------------------------------------------------
    # ABA 3: PREDIÇÕES
    # ----------------------------------------------------------
    def _build_predictions_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Predições   ")

        btn = ttk.Button(tab, text="Atualizar lista", command=self._refresh_predictions)
        btn.pack(anchor="w", padx=8, pady=6)

        cols = ("symbol", "signal", "score", "price", "file")
        self.pred_tree = ttk.Treeview(tab, columns=cols, show="headings", height=20)
        heads = {"symbol": "Símbolo", "signal": "Sinal", "score": "Score",
                 "price": "Preço", "file": "Arquivo"}
        widths = {"symbol": 100, "signal": 100, "score": 80, "price": 100, "file": 260}
        for c in cols:
            self.pred_tree.heading(c, text=heads[c])
            self.pred_tree.column(c, width=widths[c], anchor="center")
        self.pred_tree.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self._refresh_predictions()

    def _refresh_predictions(self) -> None:
        for iid in self.pred_tree.get_children():
            self.pred_tree.delete(iid)
        files = sorted(MQL_DATA.glob("prediction_*.json"))
        for p in files:
            try:
                import json as _j

                data = _j.loads(p.read_text(encoding="utf-8"))
                self.pred_tree.insert(
                    "",
                    "end",
                    values=(
                        data.get("symbol", "-"),
                        data.get("signal", "-"),
                        data.get("score", "-"),
                        data.get("price", "-"),
                        p.name,
                    ),
                )
            except Exception:
                continue

    # ----------------------------------------------------------
    # ABA 4: API / CONEXÕES
    # ----------------------------------------------------------
    def _build_api_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   API / Conexões   ")

        cfg = cs.get_api_config()

        frm = ttk.LabelFrame(tab, text="Credenciais de API (salvas em Ultimate/config.json)")
        frm.pack(fill="x", padx=10, pady=8)

        def row(f, lbl, key, show):
            ttk.Label(f, text=lbl).grid(sticky="w", pady=3)
            var = tk.StringVar(value=cfg.get(key, ""))
            ent = ttk.Entry(f, textvariable=var, width=52, show=show)
            ent.grid(row=int(len(f.grid_slaves()) / 2), column=1, sticky="we", padx=6, pady=3)
            return var

        self.api_vars: dict[str, tk.StringVar] = {
            "broker_api_key": row(frm, "Broker API Key:", "broker_api_key", ""),
            "broker_api_secret": row(frm, "Broker API Secret:", "broker_api_secret", "*"),
            "alpha_api_key": row(frm, "Alpha Vantage Key:", "alpha_api_key", ""),
            "brave_api_key": row(frm, "Brave Search Key:", "brave_api_key", ""),
        }

        ttk.Button(frm, text="Salvar credenciais", command=self._save_api_section).grid(
            row=6, column=0, columnspan=2, pady=8
        )

        serv = ttk.LabelFrame(tab, text="Serviços / Teste de conexão")
        serv.pack(fill="x", padx=10, pady=8)
        for t, fn in [
            ("Testar Backend (8000)", lambda: self._test("backend")),
            ("Testar Dashboard (8501)", lambda: self._test("dashboard")),
            ("Testar LiteLLM (4000)", lambda: self._test("proxy")),
            ("Abrir Dashboard no navegador", lambda: self._open_browser()),
        ]:
            ttk.Button(serv, text=t, command=fn).pack(anchor="w", padx=6, pady=2)

        self.api_log = scrolledtext.ScrolledText(tab, height=8, state="disabled",
                                                 font=("Consolas", 9))
        self.api_log.pack(fill="both", expand=True, padx=10, pady=8)

    def _apilog(self, text: str) -> None:
        self.api_log.configure(state="normal")
        self.api_log.insert("end", text + "\n")
        self.api_log.see("end")
        self.api_log.configure(state="disabled")

    def _save_api_section(self) -> None:
        payload = {k: v.get() for k, v in self.api_vars.items()}
        cs.save_api_config(payload)
        self._apilog("[OK] Credenciais salvas em Ultimate/config.json")
        messagebox.showinfo("API", "Credenciais salvas com sucesso.")

    def _test(self, which: str) -> None:
        cfg = cs.get_api_config()
        if which == "backend":
            port = cfg.get("backend_port", 8000)
        elif which == "dashboard":
            port = cfg.get("dashboard_port", 8501)
        else:
            port = cfg.get("litellm_port", 4000)
        ok = is_port_open(int(port))
        self._apilog(f"[{'OK' if ok else 'OFFLINE'}] {which} na porta {port}")
        return

    def _open_browser(self) -> None:
        import webbrowser

        cfg = cs.get_api_config()
        webbrowser.open(f"http://127.0.0.1:{cfg.get('dashboard_port', 8501)}")

    # ----------------------------------------------------------
    # ABA 5: TREINAMENTO / AUTO-APPROVE
    # ----------------------------------------------------------
    def _build_training_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Treinamento   ")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text="Treinar modelos", command=self._run_train).pack(side="left", padx=4)
        ttk.Button(top, text="Gerar predições", command=self._run_predict).pack(side="left", padx=4)
        ttk.Button(top, text="▶ Auto-approve completo", command=self._run_autoapprove).pack(
            side="left", padx=4
        )
        self.train_state = tk.StringVar(value="ocioso")
        ttk.Label(top, textvariable=self.train_state, foreground="#05a").pack(
            side="left", padx=10
        )

        # ------------------------------------------------
        # AUTO-TREINAMENTO COM INTERVALOS
        # ------------------------------------------------
        auto = ttk.LabelFrame(tab, text="Auto-treinamento (agendado)")
        auto.pack(fill="x", padx=8, pady=(0, 6))

        ttk.Label(auto, text="Executar a cada (minutos):").pack(side="left", padx=6, pady=6)
        self.auto_interval_var = tk.StringVar(value="60")
        ttk.Spinbox(auto, from_=1, to=1440, textvariable=self.auto_interval_var,
                    width=6).pack(side="left", pady=6)
        self.auto_btn = ttk.Button(auto, text="▶ Iniciar agendamento",
                                   command=self._toggle_auto_train)
        self.auto_btn.pack(side="left", padx=8, pady=6)
        self.auto_state = tk.StringVar(value="desligado")
        ttk.Label(auto, textvariable=self.auto_state, foreground="#05a").pack(
            side="left", padx=6
        )
        ttk.Label(auto, text="(relatório automático em Reports/)",
                  foreground="#888").pack(side="left", padx=8)

        self.train_log = scrolledtext.ScrolledText(tab, state="disabled",
                                                   font=("Consolas", 9))
        self.train_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._auto_stop = threading.Event()
        self._auto_thread = None

    def _toggle_auto_train(self) -> None:
        if self._auto_thread is not None and self._auto_thread.is_alive():
            self._auto_stop.set()
            self._auto_thread = None
            self.auto_state.set("desligado")
            self.auto_btn.configure(text="▶ Iniciar agendamento")
            self.log("Auto-treinamento interrompido.")
            return

        try:
            interval = int(self.auto_interval_var.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Auto-treinamento", "Intervalo inválido.")
            return

        self._auto_stop.clear()
        self._auto_thread = threading.Thread(
            target=self._auto_train_loop, args=(interval,), daemon=True
        )
        self._auto_thread.start()
        self.auto_state.set(f"agendado a cada {interval} min")
        self.auto_btn.configure(text="■ Parar agendamento")
        self.log(f"Auto-treinamento iniciado: a cada {interval} minuto(s).")

    def _auto_train_loop(self, interval_min: int) -> None:
        import time as _t

        while not self._auto_stop.is_set():
            # primeira execução imediata
            self.msg_queue.put(("status", "Auto-treinamento: executando ciclo..."))
            self.log(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo automático iniciado.")
            try:
                import auto_engine as ae

                rep = ae.run_full()
                self.msg_queue.put(("done", ("auto", rep)))
            except Exception as e:
                self.msg_queue.put(("done", ("auto", {"erro": str(e)})))
            self.log(f"Próximo ciclo em {interval_min} minuto(s).")
            self._t.sleep(interval_min * 60)

    def _task_worker(self, kind: str) -> None:
        try:
            self.msg_queue.put(("status", f"Executando {kind}..."))
            if kind == "treinar":
                import subprocess as _sp

                r = _sp.run([_py(), "train.py"], cwd=str(PY_DIR),
                            capture_output=True, text=True, timeout=1800)
                self.msg_queue.put(("done", ("treinar", r)))
            elif kind == "predizer":
                import subprocess as _sp

                r = _sp.run([_py(), "predict.py"], cwd=str(PY_DIR),
                            capture_output=True, text=True, timeout=1800)
                self.msg_queue.put(("done", ("predizer", r)))
            elif kind == "auto":
                import auto_engine as ae

                rep = ae.run_full()
                self.msg_queue.put(("done", ("auto", rep)))
        except Exception as e:
            self.msg_queue.put(("done", (kind, e)))

    def _run_train(self) -> None:
        self._spawn_task("treinar")

    def _run_predict(self) -> None:
        self._spawn_task("predizer")

    def _run_autoapprove(self) -> None:
        self._spawn_task("auto")

    def _spawn_task(self, kind: str) -> None:
        self.train_state.set("executando...")
        self.log(f"==> Iniciando: {kind}")
        threading.Thread(target=self._task_worker, args=(kind,), daemon=True).start()

    def _on_task_done(self, payload) -> None:
        kind, result = payload
        self.train_state.set("concluído")
        if kind == "treinar":
            r = result
            self.log("\n---------- TREINAR ----------")
            self.log("Código de saída: " + str(getattr(r, "returncode", "?")))
            self.log((getattr(r, "stdout", "") or "")[-1600:])
            if getattr(r, "stderr", ""):
                self.log("[stderr] " + getattr(r, "stderr", "")[-600:])
        elif kind == "predizer":
            r = result
            self.log("\n---------- PREDIZER ----------")
            self.log("Código de saída: " + str(getattr(r, "returncode", "?")))
            self.log((getattr(r, "stdout", "") or "")[-1600:])
            self._refresh_predictions()
        elif kind == "auto":
            rep = result if isinstance(result, dict) else {"erro": str(result)}
            self.log("\n---------- AUTO-APPROVE ----------")
            self.log(f"Relatório: {rep.get('report_file', '-')}")
            self.log(f"Aprovado: {rep.get('verdict', {}).get('approved')}")
            for ch in rep.get("verdict", {}).get("checks", []):
                self.log(f"  [{'v' if ch['ok'] else 'x'}] {ch['name']}: {ch['detail']}")
            self.log(f"Predictions geradas: {len(rep.get('predictions', []))}")
        else:
            self.log(str(result))
        self.log("==> Concluído\n")
        self.set_status("Tarefa concluída.")

        # ----------------------------------------------------------
    # ABA 4: INTEGRACAO MT5 + ROBO (visual moderno estilo Figma)
    # ----------------------------------------------------------
    def _build_mt5_tab(self) -> None:
        tab = tk.Frame(self.nb, bg=self.colors.BG)
        self.nb.add(tab, text="   MT5 / Robo   ")

        canvas = tk.Canvas(tab, bg=self.colors.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=self.colors.BG)
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", width=880)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        cfg = cs.load_config()

        # Conexao
        conn_card = ds.Card(scrollable, theme=self.current_theme, title="Conexao MetaTrader 5")
        conn_card.pack(fill="x", padx=16, pady=12)
        row1 = tk.Frame(conn_card.body, bg=self.colors.CARD)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Terminal:", bg=self.colors.CARD, fg=self.colors.TEXT2,
                 font=("Segoe UI", 10)).pack(side="left")
        self.mt5_path_var = tk.StringVar(value=self._mt5_get_terminal_path())
        tk.Entry(row1, textvariable=self.mt5_path_var, width=55, bg=self.colors.PANEL,
                 fg=self.colors.TEXT, insertbackground=self.colors.TEXT,
                 relief="flat", highlightthickness=1, highlightbackground=self.colors.BORDER_COLOR).pack(side="left", padx=8)
        ds.SecondaryButton(row1, theme=self.current_theme, text="Procurar...",
                           command=self._mt5_browse_terminal, width=12).pack(side="left", padx=4)

        row2 = tk.Frame(conn_card.body, bg=self.colors.CARD)
        row2.pack(fill="x", pady=8)
        ds.PrimaryButton(row2, theme=self.current_theme, text="Conectar",
                         command=self._mt5_connect, width=14).pack(side="left", padx=4)
        ds.SecondaryButton(row2, theme=self.current_theme, text="Desconectar",
                           command=self._mt5_disconnect, width=14).pack(side="left", padx=4)
        ds.SecondaryButton(row2, theme=self.current_theme, text="Testar conta",
                           command=self._mt5_test, width=14).pack(side="left", padx=4)
        self.mt5_state = tk.StringVar(value="desconectado")
        ds.StatusBadge(row2, theme=self.current_theme, textvariable=self.mt5_state,
                       status="offline").pack(side="left", padx=12)

        # KPIs da conta
        self.mt5_metrics = tk.Frame(scrollable, bg=self.colors.BG)
        self.mt5_metrics.pack(fill="x", padx=16, pady=6)
        self.metric_balance = ds.Metric(self.mt5_metrics, theme=self.current_theme,
                                        label="Balance", value="--")
        self.metric_balance.pack(side="left", fill="both", expand=True, padx=6)
        self.metric_equity = ds.Metric(self.mt5_metrics, theme=self.current_theme,
                                       label="Equity", value="--")
        self.metric_equity.pack(side="left", fill="both", expand=True, padx=6)
        self.metric_profit = ds.Metric(self.mt5_metrics, theme=self.current_theme,
                                       label="Lucro / Prejuizo", value="--")
        self.metric_profit.pack(side="left", fill="both", expand=True, padx=6)
        self.metric_margin = ds.Metric(self.mt5_metrics, theme=self.current_theme,
                                       label="Margem Livre", value="--")
        self.metric_margin.pack(side="left", fill="both", expand=True, padx=6)

        # Painel de ordens
        order_card = ds.Card(scrollable, theme=self.current_theme, title="Enviar Ordem Manual")
        order_card.pack(fill="x", padx=16, pady=12)
        orow = tk.Frame(order_card.body, bg=self.colors.CARD)
        orow.pack(fill="x", pady=4)
        tk.Label(orow, text="Simbolo:", bg=self.colors.CARD, fg=self.colors.TEXT2).pack(side="left")
        self.mt5_order_symbol = ttk.Combobox(orow, values=SYMBOLS_DEFAULT, width=12, state="normal")
        self.mt5_order_symbol.set(cfg.get("trading", {}).get("asset", "XAUUSD"))
        self.mt5_order_symbol.pack(side="left", padx=6)

        tk.Label(orow, text="Tipo:", bg=self.colors.CARD, fg=self.colors.TEXT2).pack(side="left")
        self.mt5_order_type = ttk.Combobox(orow, values=["BUY", "SELL"], width=10, state="readonly")
        self.mt5_order_type.set("BUY")
        self.mt5_order_type.pack(side="left", padx=6)
        tk.Label(orow, text="Volume:", bg=self.colors.CARD, fg=self.colors.TEXT2).pack(side="left")
        self.mt5_order_volume = tk.Entry(orow, width=10, bg=self.colors.PANEL, fg=self.colors.TEXT,
                                         insertbackground=self.colors.TEXT, relief="flat",
                                         highlightthickness=1, highlightbackground=self.colors.BORDER_COLOR)
        self.mt5_order_volume.insert(0, "0.01")
        self.mt5_order_volume.pack(side="left", padx=6)
        tk.Label(orow, text="SL:", bg=self.colors.CARD, fg=self.colors.TEXT2).pack(side="left")
        self.mt5_order_sl = tk.Entry(orow, width=10, bg=self.colors.PANEL, fg=self.colors.TEXT,
                                     insertbackground=self.colors.TEXT, relief="flat",
                                     highlightthickness=1, highlightbackground=self.colors.BORDER_COLOR)
        self.mt5_order_sl.insert(0, "0")
        self.mt5_order_sl.pack(side="left", padx=6)
        tk.Label(orow, text="TP:", bg=self.colors.CARD, fg=self.colors.TEXT2).pack(side="left")
        self.mt5_order_tp = tk.Entry(orow, width=10, bg=self.colors.PANEL, fg=self.colors.TEXT,
                                     insertbackground=self.colors.TEXT, relief="flat",
                                     highlightthickness=1, highlightbackground=self.colors.BORDER_COLOR)
        self.mt5_order_tp.insert(0, "0")
        self.mt5_order_tp.pack(side="left", padx=6)
        ds.PrimaryButton(orow, theme=self.current_theme, text="Enviar Ordem",
                         command=self._mt5_send_order, width=14).pack(side="left", padx=10)

        # Posicoes abertas
        pos_card = ds.Card(scrollable, theme=self.current_theme, title="Posicoes Abertas")
        pos_card.pack(fill="both", expand=True, padx=16, pady=12)
        self.mt5_positions_tree = ttk.Treeview(
            pos_card.body, columns=("ticket", "symbol", "type", "volume", "price", "sl", "tp", "profit"),
            show="headings", height=6
        )
        for col, txt in [("ticket", "Ticket"), ("symbol", "Simbolo"), ("type", "Tipo"),
                         ("volume", "Volume"), ("price", "Preco"), ("sl", "SL"),
                         ("tp", "TP"), ("profit", "Lucro")]:
            self.mt5_positions_tree.heading(col, text=txt)
            self.mt5_positions_tree.column(col, anchor="center")
        self.mt5_positions_tree.pack(fill="both", expand=True, padx=4, pady=4)
        btn_pos = tk.Frame(pos_card.body, bg=self.colors.CARD)
        btn_pos.pack(fill="x", pady=4)
        ds.SecondaryButton(btn_pos, theme=self.current_theme, text="Atualizar posicoes",
                           command=self._mt5_refresh_positions, width=18).pack(side="left", padx=4)
        ds.SecondaryButton(btn_pos, theme=self.current_theme, text="Fechar posicao selecionada",
                           command=self._mt5_close_selected, width=24).pack(side="left", padx=4)

        # Historico
        hist_card = ds.Card(scrollable, theme=self.current_theme, title="Historico de Deals 7 dias")
        hist_card.pack(fill="both", expand=True, padx=16, pady=12)
        self.mt5_history_tree = ttk.Treeview(
            hist_card.body, columns=("ticket", "time", "symbol", "type", "volume", "price", "profit"),
            show="headings", height=6
        )
        for col, txt in [("ticket", "Ticket"), ("time", "Horario"), ("symbol", "Simbolo"),
                         ("type", "Tipo"), ("volume", "Volume"), ("price", "Preco"), ("profit", "Lucro")]:
            self.mt5_history_tree.heading(col, text=txt)
            self.mt5_history_tree.column(col, anchor="center")
        self.mt5_history_tree.pack(fill="both", expand=True, padx=4, pady=4)
        ds.SecondaryButton(hist_card.body, theme=self.current_theme, text="Atualizar historico",
                           command=self._mt5_refresh_history, width=18).pack(anchor="w", padx=4, pady=4)

        # Controle do robo
        robot_card = ds.Card(scrollable, theme=self.current_theme, title="Robo XAU AI PRO")
        robot_card.pack(fill="x", padx=16, pady=12)
        rrow = tk.Frame(robot_card.body, bg=self.colors.CARD)
        rrow.pack(fill="x", pady=4)
        ds.PrimaryButton(rrow, theme=self.current_theme, text="Iniciar Robo",
                         command=self._mt5_start_robot, width=14).pack(side="left", padx=4)
        ds.SecondaryButton(rrow, theme=self.current_theme, text="Parar Robo",
                           command=self._mt5_stop_robot, width=14).pack(side="left", padx=4)
        ds.SecondaryButton(rrow, theme=self.current_theme, text="Status do Robo",
                           command=self._mt5_robot_status, width=16).pack(side="left", padx=4)
        self.mt5_robot_state = tk.StringVar(value="nao verificado")
        ds.StatusBadge(rrow, theme=self.current_theme, textvariable=self.mt5_robot_state,
                       status="offline").pack(side="left", padx=12)

        # Log MT5
        log_card = ds.Card(scrollable, theme=self.current_theme, title="Log MT5")
        log_card.pack(fill="both", expand=True, padx=16, pady=12)
        self.mt5_log = scrolledtext.ScrolledText(log_card.body, height=8, state="disabled",
                                                  font=("Consolas", 9), wrap="word")
        self.mt5_log.pack(fill="both", expand=True, padx=4, pady=4)

    def _mt5_log(self, text: str) -> None:
        self.mt5_log.configure(state="normal")
        self.mt5_log.insert("end", f"{datetime.now().strftime('%H:%M:%S')}  {text}\n")
        self.mt5_log.see("end")
        self.mt5_log.configure(state="disabled")

    def _mt5_send_order(self) -> None:
        symbol = self.mt5_order_symbol.get().strip()
        order_type = self.mt5_order_type.get()
        try:
            volume = float(self.mt5_order_volume.get())
            sl = float(self.mt5_order_sl.get())
            tp = float(self.mt5_order_tp.get())
        except ValueError:
            messagebox.showwarning("Ordem", "Volume, SL e TP devem ser numeros.")
            return
        self._mt5_log(f"Enviando ordem {order_type} {volume} em {symbol}...")
        threading.Thread(target=self._mt5_send_order_thread,
                         args=(symbol, order_type, volume, sl, tp), daemon=True).start()

    def _mt5_send_order_thread(self, symbol: str, order_type: str, volume: float, sl: float, tp: float) -> None:
        try:
            res = mi.send_order(symbol, order_type, volume, sl, tp)
            if res.get("ok"):
                self.msg_queue.put(("mt5_order", f"Ordem executada: ticket {res['ticket']} @ {res['price']}"))
                try:
                    import slack_notifier as _sn
                    _sn.send_info("ORDEM MANUAL", f"{order_type} {volume} {symbol} @ {res['price']} (ticket {res['ticket']})")
                except Exception:
                    pass
            else:
                self.msg_queue.put(("mt5_order", f"Erro na ordem: {res.get('error', '?')}"))
                try:
                    import slack_notifier as _sn
                    _sn.send_error("ORDEM MANUAL", f"{symbol}: {res.get('error', '?')}")
                except Exception:
                    pass
        except Exception as e:
            self.msg_queue.put(("mt5_order", f"Excecao: {e}"))

    def _mt5_refresh_positions(self) -> None:
        threading.Thread(target=self._mt5_refresh_positions_thread, daemon=True).start()

    def _mt5_refresh_positions_thread(self) -> None:
        try:
            positions = mi.get_positions()
            self.msg_queue.put(("mt5_positions", positions))
        except Exception as e:
            self.msg_queue.put(("mt5_positions", []))
            self.msg_queue.put(("status", f"MT5 posicoes: {e}"))

    def _mt5_refresh_history(self) -> None:
        threading.Thread(target=self._mt5_refresh_history_thread, daemon=True).start()

    def _mt5_refresh_history_thread(self) -> None:
        try:
            deals = mi.get_history(days=7)
            self.msg_queue.put(("mt5_history", deals))
        except Exception as e:
            self.msg_queue.put(("mt5_history", []))
            self.msg_queue.put(("status", f"MT5 historico: {e}"))

    def _mt5_close_selected(self) -> None:
        sel = self.mt5_positions_tree.selection()
        if not sel:
            messagebox.showwarning("Fechar", "Selecione uma posicao na tabela.")
            return
        ticket = int(self.mt5_positions_tree.item(sel[0])["values"][0])
        self._mt5_log(f"Fechando posicao {ticket}...")
        threading.Thread(target=self._mt5_close_thread, args=(ticket,), daemon=True).start()

    def _mt5_close_thread(self, ticket: int) -> None:
        try:
            res = mi.close_position(ticket)
            self.msg_queue.put(("mt5_close", res))
            try:
                import slack_notifier as _sn
                if res.get("ok"):
                    _sn.send_info("POSICAO", f"Posicao {ticket} fechada manualmente")
                else:
                    _sn.send_error("POSICAO", f"Falha ao fechar {ticket}: {res.get('error', '?')}")
            except Exception:
                pass
        except Exception as e:
            self.msg_queue.put(("status", f"MT5 close: {e}"))

    def _mt5_update_metrics(self) -> None:
        try:
            info = mi.get_account_info()
            if info is None:
                return
            profit = info.get("profit", 0.0)
            profit_color = self.colors.SUCCESS if profit >= 0 else self.colors.DANGER
            self.metric_balance.metric_value.config(text=f"{info.get('balance', 0.0):,.2f}")
            self.metric_equity.metric_value.config(text=f"{info.get('equity', 0.0):,.2f}")
            self.metric_profit.metric_value.config(text=f"{profit:,.2f}", fg=profit_color)
            self.metric_margin.metric_value.config(text=f"{info.get('margin_free', 0.0):,.2f}")
        except Exception:
            pass

    def _mt5_update_positions_table(self, positions: list) -> None:
        for iid in self.mt5_positions_tree.get_children():
            self.mt5_positions_tree.delete(iid)
        for p in positions:
            self.mt5_positions_tree.insert(
                "", "end",
                values=(p.ticket, p.symbol, p.type, p.volume,
                        f"{p.open_price:.5f}", f"{p.sl:.5f}", f"{p.tp:.5f}", f"{p.profit:.2f}")
            )

    def _mt5_update_history_table(self, deals: list) -> None:
        for iid in self.mt5_history_tree.get_children():
            self.mt5_history_tree.delete(iid)
        for d in deals:
            self.mt5_history_tree.insert(
                "", "end",
                values=(d.ticket, d.time, d.symbol, d.type, d.volume,
                        f"{d.price:.5f}", f"{d.profit:.2f}")
            )

    # ---- Helpers MT5 ----
    def _mt5_get_terminal_path(self) -> str:
        cfg = cs.load_config()
        return cfg.get("api", {}).get(
            "mt5_terminal_path",
            "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        )

    def _mt5_browse_terminal(self) -> None:
        try:
            path = filedialog.askopenfilename(
                title="Selecione o terminal64.exe do MetaTrader 5",
                filetypes=[("EXE", "*.exe")],
                initialdir="C:\\Program Files\\",
            )
            if path:
                self.mt5_path_var.set(path)
        except Exception:
            pass

    def _mt5_connect(self) -> None:
        self.mt5_state.set("conectando...")
        threading.Thread(target=self._mt5_connect_thread, daemon=True).start()

    def _mt5_connect_thread(self) -> None:
        try:
            path = self.mt5_path_var.get()
            self.msg_queue.put(("status", "Conectando ao MT5..."))
            ok = mi.connect_mt5(path=path)
            if ok:
                self.mt5_state.set("ONLINE")
                self.msg_queue.put(("status", "MT5 conectado com sucesso."))
                self._mt5_update_metrics()
            else:
                self.mt5_state.set("offline")
                self.msg_queue.put(("status", "MT5: falha na conexao."))
        except Exception as e:
            self.mt5_state.set("erro")
            self.msg_queue.put(("status", f"MT5: {e}"))

    def _mt5_disconnect(self) -> None:
        try:
            mi.disconnect_mt5()
            self.mt5_state.set("desconectado")
            self.msg_queue.put(("status", "MT5 desconectado."))
        except Exception as e:
            self.msg_queue.put(("status", f"MT5 disconnect: {e}"))

    def _mt5_test(self) -> None:
        self.mt5_state.set("testando...")
        threading.Thread(target=self._mt5_test_thread, daemon=True).start()

    def _mt5_test_thread(self) -> None:
        try:
            info = mi.get_account_info()
            if info:
                self.mt5_state.set("ONLINE")
                self.msg_queue.put(("status", f"MT5 OK - conta: {info.get('login')}"))
                self._mt5_update_metrics()
                self.msg_queue.put(("mt5_positions", mi.get_positions()))
                self.msg_queue.put(("mt5_history", mi.get_history()))
            else:
                self.mt5_state.set("offline")
                self.msg_queue.put(("status", "MT5: nenhuma conta conectada."))
        except Exception as e:
            self.mt5_state.set("erro")
            self.msg_queue.put(("status", f"MT5 test: {e}"))

    def _mt5_start_robot(self) -> None:
        self.mt5_robot_state.set("ativando...")
        threading.Thread(target=self._mt5_start_robot_thread, daemon=True).start()

    def _mt5_start_robot_thread(self) -> None:
        try:
            ok = mi.start_robot()
            self.mt5_robot_state.set("ATIVO" if ok else "FALHOU")
            self.msg_queue.put(("status", f"Robo: {'ATIVO' if ok else 'FALHOU'}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robo start: {e}"))

    def _mt5_stop_robot(self) -> None:
        self.mt5_robot_state.set("parando...")
        threading.Thread(target=self._mt5_stop_robot_thread, daemon=True).start()

    def _mt5_stop_robot_thread(self) -> None:
        try:
            ok = mi.stop_robot()
            self.mt5_robot_state.set("PARADO" if ok else "NAO PARADO")
            self.msg_queue.put(("status", f"Robo: {'PARADO' if ok else 'NAO PARADO'}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robo stop: {e}"))

    def _mt5_robot_status(self) -> None:
        self.mt5_robot_state.set("consultando...")
        threading.Thread(target=self._mt5_robot_status_thread, daemon=True).start()

    def _mt5_robot_status_thread(self) -> None:
        try:
            status = mi.robot_status()
            self.mt5_robot_state.set(status or "desconhecido")
            self.msg_queue.put(("status", f"Status robo: {status}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robo status: {e}"))

    # ----------------------------------------------------------
    # ABA 7: ASSISTENTE IA (chat com memoria)
    # ----------------------------------------------------------
    def _build_assistant_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Assistente IA   ")

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Pergunte ao assistente do XAU AI PRO:").pack(side="left")
        ttk.Button(top, text="Exportar conversa", command=self._export_chat).pack(side="right", padx=4)
        ttk.Button(top, text="Limpar historico", command=self._clear_chat).pack(side="right", padx=4)
        ttk.Button(top, text="Dica rapida", command=self._assistant_tip).pack(side="right", padx=4)

        self.chat_text = scrolledtext.ScrolledText(tab, state="disabled", wrap="word",
                                                   font=("Segoe UI", 10), height=18)
        self.chat_text.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        bottom = ttk.Frame(tab)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.chat_input = ttk.Entry(bottom)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_input.bind("<Return>", lambda e: self._send_chat())
        ttk.Button(bottom, text="Enviar", command=self._send_chat).pack(side="left")

        self._load_chat_history()

    def _load_chat_history(self) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.delete("1.0", "end")
        for h in self.assistant.memory.get_history(limit=30):
            role = "Voce" if h["role"] == "user" else "Assistente"
            self.chat_text.insert("end", f"{role}: {h['content']}\n\n")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _send_chat(self) -> None:
        msg = self.chat_input.get().strip()
        if not msg:
            return
        self.chat_input.delete(0, "end")
        self._append_chat(f"Voce: {msg}\n")
        self.set_status("Assistente esta pensando...")
        threading.Thread(target=self._chat_thread, args=(msg,), daemon=True).start()

    def _chat_thread(self, msg: str) -> None:
        try:
            reply = self.assistant.chat(msg)
            self.msg_queue.put(("chat", reply))
        except Exception as e:
            self.msg_queue.put(("chat", f"[ERRO] {e}"))

    def _append_chat(self, text: str) -> None:
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", text + "\n")
        self.chat_text.configure(state="disabled")
        self.chat_text.see("end")

    def _clear_chat(self) -> None:
        self.assistant.memory.clear_history()
        self._load_chat_history()

    def _assistant_tip(self) -> None:
        tip = self.assistant.quick_tip()
        self._append_chat(f"Assistente: {tip}")

    def _export_chat(self) -> None:
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("Markdown", "*.md")],
            initialfile=f"xau_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for h in self.assistant.memory.get_history(limit=200):
                    role = "Voce" if h["role"] == "user" else "Assistente"
                    f.write(f"{role}: {h['content']}\n\n")
            messagebox.showinfo("Exportar", f"Conversa salva em:\n{path}")
        except Exception as e:
            messagebox.showerror("Exportar", f"Erro ao salvar: {e}")

    # ----------------------------------------------------------
    # ABA 8: FERRAMENTAS DO DIA A DIA
    # ----------------------------------------------------------
    def _build_tools_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Ferramentas   ")

        lot = ttk.LabelFrame(tab, text="Calculadora de Lote")
        lot.pack(fill="x", padx=10, pady=8)

        fields = [
            ("Balance", "10000"), ("Risco %", "1"), ("Stop Loss (pontos)", "300"),
            ("Tick Value", "1"), ("Tick Size", "0.01"), ("Min Lot", "0.01"), ("Max Lot", "10"),
        ]
        self.lot_vars: dict[str, tk.StringVar] = {}
        for i, (lbl, default) in enumerate(fields):
            ttk.Label(lot, text=f"{lbl}:").grid(row=i, column=0, sticky="e", pady=2)
            var = tk.StringVar(value=default)
            self.lot_vars[lbl] = var
            ttk.Entry(lot, textvariable=var, width=14).grid(row=i, column=1, padx=6, pady=2)

        ttk.Button(lot, text="Calcular", command=self._calc_lot).grid(
            row=0, column=2, rowspan=2, padx=10, pady=4
        )
        self.lot_result = tk.StringVar(value="Lote: -")
        ttk.Label(lot, textvariable=self.lot_result, foreground="#0a0",
                  font=("Segoe UI", 11, "bold")).grid(row=2, column=2, rowspan=2, padx=10)

        clock = ttk.LabelFrame(tab, text="Relogio Mundial & Sessoes")
        clock.pack(fill="x", padx=10, pady=8)
        self.clock_text = tk.Text(clock, height=6, state="disabled", font=("Consolas", 10))
        self.clock_text.pack(fill="x", padx=6, pady=6)
        self._refresh_clock()
        ttk.Button(clock, text="Atualizar", command=self._refresh_clock).pack(anchor="w", padx=6, pady=(0, 6))

        cal = ttk.LabelFrame(tab, text="Calendario Economico (resumo)")
        cal.pack(fill="both", expand=True, padx=10, pady=8)
        self.cal_tree = ttk.Treeview(cal, columns=("time", "event", "impact"), show="headings", height=8)
        self.cal_tree.heading("time", text="Horario")
        self.cal_tree.heading("event", text="Evento")
        self.cal_tree.heading("impact", text="Impacto")
        self.cal_tree.column("time", width=100, anchor="center")
        self.cal_tree.column("event", width=500)
        self.cal_tree.column("impact", width=80, anchor="center")
        self.cal_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self._refresh_calendar()

    def _refresh_clock(self) -> None:
        """Atualiza o relogio mundial e o status das sessoes de forex."""
        try:
            clocks = daily_tools.world_clocks()
            sessions = daily_tools.market_session_status()
            lines = [
                "  |  ".join("%s: %s" % (c, h) for c, h in clocks.items()),
                "",
                "Sessoes: "
                + "  |  ".join("%s: %s" % (n, s) for n, s in sessions.items()),
            ]
            self.clock_text.config(state="normal")
            self.clock_text.delete("1.0", "end")
            self.clock_text.insert("1.0", "\n".join(lines))
            self.clock_text.config(state="disabled")
        except Exception as exc:
            self.clock_text.config(state="normal")
            self.clock_text.delete("1.0", "end")
            self.clock_text.insert("1.0", "Erro ao carregar relogio: %s" % exc)
            self.clock_text.config(state="disabled")

    def _refresh_calendar(self) -> None:
        """Preenche o calendario economico (resumo)."""
        try:
            events = daily_tools.economic_calendar_simple()
            for item in self.cal_tree.get_children():
                self.cal_tree.delete(item)
            for ev in events:
                self.cal_tree.insert(
                    "",
                    "end",
                    values=(
                        ev.get("time", ""),
                        ev.get("event", ""),
                        ev.get("impact", ""),
                    ),
                )
        except Exception as exc:
            for item in self.cal_tree.get_children():
                self.cal_tree.delete(item)
            self.cal_tree.insert("", "end", values=("--", "Erro: %s" % exc, "--"))

    def _calc_lot(self) -> None:
        try:
            result = daily_tools.calculate_lot(
                balance=float(self.lot_vars["Balance"].get()),
                risk_pct=float(self.lot_vars["Risco %"].get()),
                stop_loss_points=float(self.lot_vars["Stop Loss (pontos)"].get()),
                tick_value=float(self.lot_vars["Tick Value"].get()),
                tick_size=float(self.lot_vars["Tick Size"].get()),
                min_lot=float(self.lot_vars["Min Lot"].get()),
                max_lot=float(self.lot_vars["Max Lot"].get()),
            )
            if result.get("error"):
                self.lot_result.set(f"Erro: {result['error']}")
            else:
                self.lot_result.set(
                    f"Lote: {result['lot']}  |  Risco: ${result['risk_amount']}"
                )
        except Exception as e:
            self.lot_result.set(f"Erro: {e}")

    # ----------------------------------------------------------
    # ABA 9: INTEGRACOES (GitHub, Figma, Brave)
    # ----------------------------------------------------------
    def _build_integrations_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Integracoes   ")

        cfg = cs.get_api_config()

        gh = ttk.LabelFrame(tab, text="GitHub")
        gh.pack(fill="x", padx=10, pady=8)
        ttk.Label(gh, text="Token de acesso pessoal:").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self.gh_token = tk.StringVar(value=cfg.get("github_token", ""))
        ttk.Entry(gh, textvariable=self.gh_token, width=60, show="*").grid(row=0, column=1, padx=6, pady=3)
        ttk.Button(gh, text="Testar / Listar repos", command=self._test_github).grid(
            row=1, column=0, padx=4, pady=6
        )
        self.gh_status = tk.StringVar(value="Nao testado")
        ttk.Label(gh, textvariable=self.gh_status, foreground="#888").grid(
            row=1, column=1, sticky="w", padx=6
        )

        fg = ttk.LabelFrame(tab, text="Figma")
        fg.pack(fill="x", padx=10, pady=8)
        ttk.Label(fg, text="Token:").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self.figma_token = tk.StringVar(value=cfg.get("figma_token", ""))
        ttk.Entry(fg, textvariable=self.figma_token, width=60, show="*").grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(fg, text="Team ID:").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        self.figma_team = tk.StringVar(value=cfg.get("figma_team_id", ""))
        ttk.Entry(fg, textvariable=self.figma_team, width=40).grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Button(fg, text="Testar / Listar projetos", command=self._test_figma).grid(
            row=2, column=0, padx=4, pady=6
        )
        self.figma_status = tk.StringVar(value="Nao testado")
        ttk.Label(fg, textvariable=self.figma_status, foreground="#888").grid(
            row=2, column=1, sticky="w", padx=6
        )

        br = ttk.LabelFrame(tab, text="Brave Search")
        br.pack(fill="x", padx=10, pady=8)
        ttk.Label(br, text="API Key:").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self.brave_key = tk.StringVar(value=cfg.get("brave_api_key", ""))
        ttk.Entry(br, textvariable=self.brave_key, width=60, show="*").grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(br, text="Busca:").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        self.brave_query = ttk.Entry(br, width=50)
        self.brave_query.grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Button(br, text="Buscar", command=self._search_brave).grid(row=2, column=0, padx=4, pady=6)
        self.brave_status = tk.StringVar(value="")
        ttk.Label(br, textvariable=self.brave_status, foreground="#888").grid(
            row=2, column=1, sticky="w", padx=6
        )

        sl = ttk.LabelFrame(tab, text="Slack Notifications")
        sl.pack(fill="x", padx=10, pady=8)
        ttk.Label(sl, text="Webhook URL:").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        self.slack_webhook = tk.StringVar(value=cfg.get("slack_webhook_url", ""))
        ttk.Entry(sl, textvariable=self.slack_webhook, width=60).grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(sl, text="(https://hooks.slack.com/services/...)").grid(
            row=0, column=2, sticky="w", padx=2, foreground="#888"
        )
        self.slack_enabled = tk.BooleanVar(value=cfg.get("slack_enabled", True))
        ttk.Checkbutton(sl, text="Ativar", variable=self.slack_enabled).grid(
            row=1, column=1, sticky="w", padx=6, pady=2
        )
        self.slack_notify_trades = tk.BooleanVar(value=cfg.get("slack_notify_trades", True))
        ttk.Checkbutton(sl, text="Notificar trades", variable=self.slack_notify_trades).grid(
            row=1, column=1, sticky="e", padx=6, pady=2
        )
        self.slack_notify_errors = tk.BooleanVar(value=cfg.get("slack_notify_errors", True))
        ttk.Checkbutton(sl, text="Notificar erros", variable=self.slack_notify_errors).grid(
            row=1, column=2, sticky="w", padx=6, pady=2
        )
        self.slack_status = tk.StringVar(value="Nao testado")
        ttk.Button(sl, text="Testar conexao", command=self._test_slack).grid(
            row=2, column=0, padx=4, pady=4
        )
        ttk.Label(sl, textvariable=self.slack_status, foreground="#888").grid(
            row=2, column=1, sticky="w", padx=6
        )

        ttk.Button(tab, text="Salvar tokens", command=self._save_integration_tokens).pack(
            anchor="w", padx=10, pady=8
        )

        self.integ_log = scrolledtext.ScrolledText(tab, height=10, state="disabled",
                                                   font=("Consolas", 9))
        self.integ_log.pack(fill="both", expand=True, padx=10, pady=8)

    def _ilog(self, text: str) -> None:
        self.integ_log.configure(state="normal")
        self.integ_log.insert("end", text + "\n")
        self.integ_log.see("end")
        self.integ_log.configure(state="disabled")

    def _save_integration_tokens(self) -> None:
        cs.save_api_config({
            "github_token": self.gh_token.get(),
            "figma_token": self.figma_token.get(),
            "figma_team_id": self.figma_team.get(),
            "brave_api_key": self.brave_key.get(),
            "slack_webhook_url": self.slack_webhook.get(),
            "slack_enabled": self.slack_enabled.get(),
            "slack_notify_trades": self.slack_notify_trades.get(),
            "slack_notify_errors": self.slack_notify_errors.get(),
        })
        self._ilog("[OK] Tokens salvos.")

    def _test_slack(self) -> None:
        self.slack_status.set("testando...")
        threading.Thread(target=self._slack_thread, daemon=True).start()

    def _slack_thread(self) -> None:
        client = integrations.SlackClient(self.slack_webhook.get())
        res = client.test()
        self.msg_queue.put(("slack_test", res))

    def _test_github(self) -> None:
        self.gh_status.set("testando...")
        threading.Thread(target=self._github_thread, daemon=True).start()

    def _github_thread(self) -> None:
        client = integrations.GitHubClient(self.gh_token.get())
        res = client.test()
        self.msg_queue.put(("github_test", res))

    def _test_figma(self) -> None:
        self.figma_status.set("testando...")
        threading.Thread(target=self._figma_thread, daemon=True).start()

    def _figma_thread(self) -> None:
        client = integrations.FigmaClient(self.figma_token.get())
        res = client.list_projects(self.figma_team.get()) if self.figma_team.get() else client.test()
        self.msg_queue.put(("figma_test", res))

    def _search_brave(self) -> None:
        query = self.brave_query.get().strip()
        if not query:
            return
        self.brave_status.set("buscando...")
        threading.Thread(target=self._brave_thread, args=(query,), daemon=True).start()

    def _brave_thread(self, query: str) -> None:
        client = integrations.WebSearchClient(self.brave_key.get())
        res = client.search(query)
        self.msg_queue.put(("brave_search", res))

    # ----------------------------------------------------------
    # ABA 10: MEMORIA (pensamentos + notas diarias)
    # ----------------------------------------------------------
    def _build_memory_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Memoria   ")

        th = ttk.LabelFrame(tab, text="Pensamentos / Ideias")
        th.pack(fill="x", padx=10, pady=8)
        ttk.Label(th, text="Titulo:").grid(row=0, column=0, sticky="e", pady=2)
        self.thought_title = ttk.Entry(th, width=40)
        self.thought_title.grid(row=0, column=1, sticky="w", padx=6, pady=2)
        ttk.Label(th, text="Tags:").grid(row=1, column=0, sticky="e", pady=2)
        self.thought_tags = ttk.Entry(th, width=40)
        self.thought_tags.grid(row=1, column=1, sticky="w", padx=6, pady=2)
        ttk.Label(th, text="Conteudo:").grid(row=2, column=0, sticky="ne", pady=2)
        self.thought_body = tk.Text(th, height=4, width=60)
        self.thought_body.grid(row=2, column=1, sticky="w", padx=6, pady=2)
        ttk.Button(th, text="Salvar pensamento", command=self._save_thought).grid(
            row=3, column=1, sticky="w", padx=6, pady=6
        )

        ttk.Label(tab, text="Ultimos pensamentos salvos:").pack(anchor="w", padx=10, pady=(8, 0))
        self.thoughts_tree = ttk.Treeview(tab, columns=("id", "title", "tags", "created"), show="headings", height=6)
        self.thoughts_tree.heading("id", text="ID")
        self.thoughts_tree.heading("title", text="Titulo")
        self.thoughts_tree.heading("tags", text="Tags")
        self.thoughts_tree.heading("created", text="Data")
        self.thoughts_tree.column("id", width=40, anchor="center")
        self.thoughts_tree.column("title", width=260)
        self.thoughts_tree.column("tags", width=120)
        self.thoughts_tree.column("created", width=140)
        self.thoughts_tree.pack(fill="x", padx=10, pady=6)
        ttk.Button(tab, text="Atualizar", command=self._refresh_thoughts).pack(anchor="w", padx=10)
        ttk.Button(tab, text="Excluir selecionado", command=self._delete_thought).pack(anchor="w", padx=10, pady=(0, 8))

        note = ttk.LabelFrame(tab, text="Nota do dia")
        note.pack(fill="both", expand=True, padx=10, pady=8)
        self.daily_note_text = tk.Text(note, height=8)
        self.daily_note_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.daily_note_text.insert("1.0", self.assistant.memory.get_daily_note(datetime.now().strftime("%Y-%m-%d")))
        ttk.Button(note, text="Salvar nota", command=self._save_daily_note).pack(anchor="w", padx=6, pady=(0, 6))

        self._refresh_thoughts()

    def _save_thought(self) -> None:
        title = self.thought_title.get().strip()
        body = self.thought_body.get("1.0", "end").strip()
        tags = self.thought_tags.get().strip()
        if not title or not body:
            messagebox.showwarning("Memoria", "Titulo e conteudo sao obrigatorios.")
            return
        self.assistant.memory.add_thought(title, body, tags)
        self.thought_title.delete(0, "end")
        self.thought_body.delete("1.0", "end")
        self.thought_tags.delete(0, "end")
        self._refresh_thoughts()

    def _refresh_thoughts(self) -> None:
        for iid in self.thoughts_tree.get_children():
            self.thoughts_tree.delete(iid)
        for t in self.assistant.memory.get_thoughts(limit=50):
            self.thoughts_tree.insert("", "end", values=(t["id"], t["title"], t["tags"], t["created_at"][:19]))

    def _delete_thought(self) -> None:
        sel = self.thoughts_tree.selection()
        if not sel:
            return
        item = self.thoughts_tree.item(sel[0])
        thought_id = item["values"][0]
        self.assistant.memory.delete_thought(int(thought_id))
        self._refresh_thoughts()

    def _save_daily_note(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        content = self.daily_note_text.get("1.0", "end").strip()
        self.assistant.memory.save_daily_note(today, content)
        messagebox.showinfo("Memoria", "Nota do dia salva.")

    # ----------------------------------------------------------
    # ABA 6: CONFIGURAÇÕES
    # ----------------------------------------------------------
    def _build_config_tab(self) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text="   Configurações   ")

        cfg = cs.load_config()
        api = cfg.get("api", {})
        ui_cfg = cfg.get("ui", {})

        frm = ttk.LabelFrame(tab, text="Mercado / Trading")
        frm.pack(fill="x", padx=10, pady=8)

        ttk.Label(frm, text="Ativo padrão:").grid(row=0, column=0, sticky="e", pady=3)
        self.cfg_asset = ttk.Entry(frm, width=20)
        self.cfg_asset.insert(0, cfg.get("trading", {}).get("asset", "XAUUSD"))
        self.cfg_asset.grid(row=0, column=1, padx=6, pady=3)

        ttk.Label(frm, text="Provider de preço (auto|mt5|yfinance):").grid(
            row=1, column=0, sticky="e", pady=3
        )
        self.cfg_provider = ttk.Combobox(frm, values=["auto", "mt5", "yfinance"], width=18)
        self.cfg_provider.set(api.get("live_provider", "auto"))
        self.cfg_provider.grid(row=1, column=1, padx=6, pady=3)

        ttk.Label(frm, text="Refresh (segundos):").grid(row=2, column=0, sticky="e", pady=3)
        self.cfg_refresh = ttk.Entry(frm, width=20)
        self.cfg_refresh.insert(0, str(api.get("refresh_seconds", 5)))
        self.cfg_refresh.grid(row=2, column=1, padx=6, pady=3)

        ttk.Button(frm, text="Salvar configurações", command=self._save_config_tab).grid(
            row=3, column=0, columnspan=2, pady=8
        )

        # Theme selector
        ttk.Label(frm, text="Tema:").grid(row=4, column=0, sticky="e", pady=3)
        self.cfg_theme = ttk.Combobox(
            frm, values=themes.list_themes(), width=12, state="readonly"
        )
        self.cfg_theme.set(cfg.get("theme", "dark"))
        self.cfg_theme.grid(row=4, column=1, padx=6, pady=3, sticky="w")
        ttk.Button(frm, text="Aplicar tema", command=self._apply_theme_from_cfg).grid(
            row=5, column=0, columnspan=2, pady=4
        )

        # UI toggles
        ui = ttk.LabelFrame(tab, text="Interface")
        ui.pack(fill="x", padx=10, pady=8)
        self.cfg_wallpaper = tk.BooleanVar(value=ui_cfg.get("wallpaper_enabled", True))
        ttk.Checkbutton(ui, text="Ativar wallpaper animado no login",
                        variable=self.cfg_wallpaper).pack(anchor="w", padx=6, pady=3)
        self.cfg_animations = tk.BooleanVar(value=ui_cfg.get("animations_enabled", True))
        ttk.Checkbutton(ui, text="Ativar animacoes",
                        variable=self.cfg_animations).pack(anchor="w", padx=6, pady=3)

        usr = ttk.LabelFrame(tab, text="Usuários")
        usr.pack(fill="x", padx=10, pady=8)
        ttk.Label(usr, text="Novo usuário:").grid(row=0, column=0, sticky="e", pady=3)
        self.cfg_newuser = ttk.Entry(usr, width=18)
        self.cfg_newuser.grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(usr, text="Senha:").grid(row=0, column=2, sticky="e", pady=3)
        self.cfg_newpass = ttk.Entry(usr, width=18, show="*")
        self.cfg_newpass.grid(row=0, column=3, padx=6, pady=3)
        ttk.Button(usr, text="Criar usuário", command=self._add_user).grid(
            row=0, column=4, padx=6, pady=3
        )

        log = ttk.LabelFrame(tab, text="Logs")
        log.pack(fill="both", expand=True, padx=10, pady=8)
        self.cfg_logtext = scrolledtext.ScrolledText(log, height=10, state="disabled",
                                                     font=("Consolas", 9))
        self.cfg_logtext.pack(fill="both", expand=True, padx=6, pady=6)

    def _cfglog(self, text: str) -> None:
        self.cfg_logtext.configure(state="normal")
        self.cfg_logtext.insert("end", text + "\n")
        self.cfg_logtext.see("end")
        self.cfg_logtext.configure(state="disabled")

    def _save_config_tab(self) -> None:
        cfg = cs.load_config()
        cfg["trading"]["asset"] = self.cfg_asset.get()
        cfg["api"]["live_provider"] = self.cfg_provider.get()
        try:
            cfg["api"]["refresh_seconds"] = int(self.cfg_refresh.get())
        except ValueError:
            pass
        if hasattr(self, "mt5_path_var"):
            cfg["api"]["mt5_terminal_path"] = self.mt5_path_var.get()
        if hasattr(self, "cfg_theme"):
            cfg["theme"] = self.cfg_theme.get()
        cfg.setdefault("ui", {}).update({
            "wallpaper_enabled": self.cfg_wallpaper.get() if hasattr(self, "cfg_wallpaper") else True,
            "animations_enabled": self.cfg_animations.get() if hasattr(self, "cfg_animations") else True,
        })
        cs.save_config(cfg)
        self.apply_theme(cfg["theme"])
        self._cfglog("[OK] Configuracoes salvas.")
        messagebox.showinfo("Config", "Configuracoes salvas.")

    def _add_user(self) -> None:
        u = self.cfg_newuser.get()
        p = self.cfg_newpass.get()
        if cs.create_user(u, p):
            self._cfglog(f"[OK] Usuário '{u}' criado.")
        else:
            self._cfglog("[x] Não foi possível criar (pode já existir).")

    # ----------------------------------------------------------
    # MT5 Helper Methods
    # ----------------------------------------------------------
    def _mt5_get_terminal_path(self) -> str:
        """Retorna o caminho do executável mt5 do config_store."""
        cfg = cs.load_config()
        return cfg.get("api", {}).get(
            "mt5_terminal_path",
            "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        )

    def _mt5_browse_terminal(self) -> None:
        try:
            import filedialog

            path = filedialog.askopenfilename(
                title="Selecione o terminal64.exe do MetaTrader 5",
                filetypes=[("EXE", "*.exe")],
                initialdir="C:\\Program Files\\",
            )
            if path:
                self.mt5_path_var.set(path)
        except Exception:
            pass

    def _mt5_connect(self) -> None:
        self.mt5_state.set("conectando...")
        threading.Thread(target=self._mt5_connect_thread, daemon=True).start()

    def _mt5_connect_thread(self) -> None:
        try:
            path = self.mt5_path_var.get()
            self.msg_queue.put(("status", "Conectando ao MT5..."))
            ok = mi.connect_mt5(path=path)
            if ok:
                self.mt5_state.set("ONLINE")
                self.msg_queue.put(("status", "MT5 conectado com sucesso."))
            else:
                self.mt5_state.set("offline")
                self.msg_queue.put(("status", "MT5: falha na conexão."))
        except Exception as e:
            self.mt5_state.set("erro")
            self.msg_queue.put(("status", f"MT5: {e}"))

    def _mt5_disconnect(self) -> None:
        try:
            mi.disconnect_mt5()
            self.mt5_state.set("desconectado")
            self.msg_queue.put(("status", "MT5 desconectado."))
        except Exception as e:
            self.msg_queue.put(("status", f"MT5 disconnect: {e}"))

    def _mt5_test(self) -> None:
        self.mt5_state.set("testando...")
        threading.Thread(target=self._mt5_test_thread, daemon=True).start()

    def _mt5_test_thread(self) -> None:
        try:
            info = mi.get_account_info()
            if info:
                self.mt5_state.set("ONLINE")
                self.msg_queue.put(("status", f"MT5 OK — conta: {info.get('login')}"))
            else:
                self.mt5_state.set("offline")
                self.msg_queue.put(("status", "MT5: nenhuma conta conectada."))
        except Exception as e:
            self.mt5_state.set("erro")
            self.msg_queue.put(("status", f"MT5 test: {e}"))

    def _mt5_start_robot(self) -> None:
        self.mt5_robot_state.set("ativando...")
        threading.Thread(target=self._mt5_start_robot_thread, daemon=True).start()

    def _mt5_start_robot_thread(self) -> None:
        try:
            ok = mi.start_robot()
            self.mt5_robot_state.set("ATIVO" if ok else "FALHOU")
            self.msg_queue.put(("status", f"Robô: {'ATIVO' if ok else 'FALHOU'}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robô start: {e}"))

    def _mt5_stop_robot(self) -> None:
        self.mt5_robot_state.set("parando...")
        threading.Thread(target=self._mt5_stop_robot_thread, daemon=True).start()

    def _mt5_stop_robot_thread(self) -> None:
        try:
            ok = mi.stop_robot()
            self.mt5_robot_state.set("PARADO" if ok else "NÃO PARADO")
            self.msg_queue.put(("status", f"Robô: {'PARADO' if ok else 'NÃO PARADO'}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robô stop: {e}"))

    def _mt5_robot_status(self) -> None:
        self.mt5_robot_state.set("consultando...")
        threading.Thread(target=self._mt5_robot_status_thread, daemon=True).start()

    def _mt5_robot_status_thread(self) -> None:
        try:
            status = mi.robot_status()
            self.mt5_robot_state.set(status or "desconhecido")
            self.msg_queue.put(("status", f"Status robô: {status}"))
        except Exception as e:
            self.mt5_robot_state.set("erro")
            self.msg_queue.put(("status", f"Robô status: {e}"))


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    root = tk.Tk()
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    ttk.Style().theme_use("clam")
    XauAiProApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
