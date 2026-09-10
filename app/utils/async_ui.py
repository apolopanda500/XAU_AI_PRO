# -*- coding: utf-8 -*-
"""Utilitario de trabalho assincrono para a GUI (thread-safe).

Padrao Tkinter correto:
  - trabalho pesado (rede, socket, MT5, disco) roda em thread daemon
  - o resultado volta para a thread da GUI via widget.after(0, ...)
  - NENHUM widget e tocado fora da thread principal
  - uma flag _busy evita empilhamento de refreshes concorrentes
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def _find_scroll_host(widget: tk.Widget):
    current: tk.Widget | None = widget
    while current is not None:
        host = getattr(current, "_scroll_host", None)
        if host is not None:
            return host
        parent_name = current.winfo_parent()
        if not parent_name:
            return None
        try:
            current = current.nametowidget(parent_name)
        except tk.TclError:
            return None
    return None


def run_bg(
    root: tk.Widget,
    work: Callable[[], T],
    apply_result: Callable[[T], None],
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """Executa `work` em thread daemon e aplica o resultado na GUI thread.

    Usa a flag `root._bg_busy` para NAO empilhar execucoes concorrentes:
    se um trabalho anterior ainda estiver rodando, o novo e ignorado.
    Se `work` levantar excecao: `on_error(exc)` (default: apply_result(None)).
    """
    if getattr(root, "_bg_busy", False):
        return
    root._bg_busy = True
    scroll_host = _find_scroll_host(root)
    scroll_snapshot = scroll_host.capture_view() if scroll_host is not None else None

    def _apply_with_viewport(result: T) -> None:
        try:
            apply_result(result)
        finally:
            if scroll_host is not None and scroll_snapshot is not None:
                scroll_host.restore_view(scroll_snapshot)

    def _background() -> None:
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001
            if on_error is not None:
                try:
                    root.after(0, lambda e=exc: on_error(e))
                except Exception:
                    pass
            else:
                try:
                    root.after(0, lambda: _apply_with_viewport(None))  # type: ignore[arg-type]
                except Exception:
                    pass
        else:
            try:
                root.after(0, lambda: _apply_with_viewport(result))
            except Exception:
                pass
        finally:
            try:
                # A flag deve ser liberada na thread da GUI. Isso evita uma
                # corrida em que um refresh novo e iniciado antes da entrega
                # do resultado anterior e mantem no maximo uma tarefa ativa.
                root.after(0, lambda: setattr(root, "_bg_busy", False))
            except Exception:
                pass

    threading.Thread(target=_background, daemon=True).start()


def spawn_daemon(target: Callable[[], None]) -> threading.Thread:
    """Dispara uma funcao em thread daemon (best-effort)."""
    t = threading.Thread(target=target, daemon=True)
    try:
        t.start()
    except Exception:
        pass
    return t
