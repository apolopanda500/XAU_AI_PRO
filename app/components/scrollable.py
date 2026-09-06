# -*- coding: utf-8 -*-
"""Contêiner vertical reutilizável para abas longas da GUI.

Rotação interna:
  - Rolda APENAS o contêiner sob o ponteiro (bind LOCAL no canvas), nunca
    bind global via bind_all persistente. Assim, eventos de atualização /
    navegação não interferem na rolagem e dois contêineres não disputam a
    mesma roda.
  - Preservação de leitura: capture_view() tira um snapshot (posição +
    revisão); restore_view() só restaura a posição se o usuário NÃO rolou
    enquanto a coleta rodava (a revisão é incrementada a cada rolagem).
  - No recálculo final do layout (_update_region) a posição pendente de um
    refresh recém-concluído é aplicada via after_idle, garantindo que o
    conteúdo volte ao lugar certo após o scrollregion ser recalculado —
    nunca saltando a posição de leitura durante a atualização.
"""
from __future__ import annotations

import tkinter as tk


class ScrollableFrame(tk.Frame):
    """Frame com scrollbar e roda do mouse com bindings locais ao contêiner ativo."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=kwargs.get("bg", "#0a0b0e"))
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self._view_revision = 0
        self._pending_view: float | None = None
        self._pending_revision = 0
        self._flush_after_id: str | None = None
        self.inner = tk.Frame(self.canvas, bg=kwargs.get("bg", "#0a0b0e"))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._resize_inner)

        # Bindings da roda do mouse LOCAIS ao contêiner ativo: registramos um
        # único handler global por instância, mas só giramos quando o cursor
        # está fisicamente sobre ESTE canvas (hit-test). Assim, eventos de
        # atualização/navegação de outros contêineres jamais interferem nesta
        # rolagem, e não há bind_all cumulativo solto entre múltiplos frames.
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")
        self.canvas.bind("<ButtonPress-1>", self._mark_user_scroll)
        self.scrollbar.bind("<ButtonPress-1>", self._mark_user_scroll)

    # ------------------------------------------------------------------
    # Snapshot / restauração da leitura (chamado pelo core durante refresh)
    # ------------------------------------------------------------------
    # Debounce: a posição pendente só é aplicada após o layout ESTABILIZAR
    # (último <Configure> + 120ms). Assim o refresh assíncrono pode destruir/
    # recriar widgets à vontade — a leitura só é restaurada no fim, e nunca
    # consumida cedo demais por um evento de layout intermediário.
    _FLUSH_DEBOUNCE_MS = 120

    def capture_view(self) -> tuple[float, int]:
        """Retorna a posição atual para restaurá-la após a atualização assíncrona."""
        return self.canvas.yview()[0], self._view_revision

    def restore_view(self, snapshot: tuple[float, int]) -> None:
        """Agenda a restauração da leitura, bloqueada se o usuário rolou na coleta.

        Não aplica imediatamente: marca a posição pendente e espera o layout
        estabilizar (debounce em _update_region), pois o refresh é assíncrono
        e o conteúdo real muda DEPOIS que este método retorna.
        """
        position, revision = snapshot
        if revision != self._view_revision:
            return
        self._pending_view = position
        self._pending_revision = revision
        self._schedule_flush()

    def _schedule_flush(self) -> None:
        """Reagenda o flush: só dispara 120ms após o último evento de layout."""
        if self._flush_after_id is not None:
            try:
                self.after_cancel(self._flush_after_id)
            except Exception:
                pass
        self._flush_after_id = self.after(self._FLUSH_DEBOUNCE_MS, self._flush_pending_view)

    def _flush_pending_view(self, _event=None) -> None:
        """Aplica a posição pendente após o recálculo final do layout."""
        self._flush_after_id = None
        if self._pending_view is None:
            return
        # Se o usuário rolou enquanto a coleta/atualização rodava, descarta.
        if self._pending_revision != self._view_revision:
            self._pending_view = None
            return
        position = self._pending_view
        self._pending_view = None
        self.canvas.yview_moveto(position)

    def _update_region(self, _event=None) -> None:
        # Recalcula o scrollregion e (re)agenda a restauração da leitura
        # pendente — o debounce garante que só o ÚLTIMO evento de layout
        # dispare o flush, já depois do refresh terminar de reconstruir.
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if self._pending_view is not None:
            self._schedule_flush()

    def _resize_inner(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    # ------------------------------------------------------------------
    # Roda do mouse local ao contêiner ativo (com hit-test de cursor)
    # ------------------------------------------------------------------
    def _cursor_over_canvas(self, event) -> bool:
        """Verifica se o ponteiro está fisicamente sobre este canvas."""
        try:
            x0 = self.canvas.winfo_rootx()
            y0 = self.canvas.winfo_rooty()
            x1 = x0 + self.canvas.winfo_width()
            y1 = y0 + self.canvas.winfo_height()
            return x0 <= event.x_root <= x1 and y0 <= event.y_root <= y1
        except Exception:
            return True

    def _on_mousewheel(self, event) -> None:
        # Roda apenas o contêiner sob o cursor; os demais ignoram o evento.
        if not self._cursor_over_canvas(event):
            return
        self._mark_user_scroll()
        delta = getattr(event, "delta", 0)
        if delta == 0:
            delta = 120 if getattr(event, "num", 4) == 4 else -120
        self.canvas.yview_scroll(-max(1, abs(delta) // 120) * (1 if delta > 0 else -1), "units")

    def _mark_user_scroll(self, _event=None) -> None:
        self._view_revision += 1
        # O usuário assumiu a leitura: descarta qualquer restauração pendente
        # para nunca brigar com a rolagem manual durante um refresh.
        self._pending_view = None
        self._pending_revision = self._view_revision
        if self._flush_after_id is not None:
            try:
                self.after_cancel(self._flush_after_id)
            except Exception:
                pass
            self._flush_after_id = None