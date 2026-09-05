# -*- coding: utf-8 -*-
"""Contêiner vertical reutilizável para abas longas da GUI."""
from __future__ import annotations

import tkinter as tk


class ScrollableFrame(tk.Frame):
    """Frame com scrollbar e roda do mouse sem bind global permanente."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=kwargs.get("bg", "#0a0b0e"))
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=kwargs.get("bg", "#0a0b0e"))
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)

    def _update_region(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mouse(self, _event=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _unbind_mouse(self, _event=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event) -> None:
        delta = getattr(event, "delta", 0)
        if delta == 0:
            delta = 120 if getattr(event, "num", 4) == 4 else -120
        self.canvas.yview_scroll(-max(1, abs(delta) // 120) * (1 if delta > 0 else -1), "units")