# -*- coding: utf-8 -*-
"""Aba Comunidade local do XAU_AI_PRO.

Feed simples e persistente para anotações, ideias e observações de mercado.
O armazenamento é local e não interfere no MT5 nem no EventEmitter.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Callable

from app.components.cards import Card, PrimaryButton, SecondaryButton
from app.theme.mexc import Theme


DB_PATH = Path(__file__).resolve().parents[2] / "database" / "community.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "author TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    conn.commit()
    return conn


def list_posts(limit: int = 50) -> list[tuple[str, str, str]]:
    with _connect() as conn:
        return conn.execute(
            "SELECT author, content, created_at FROM posts ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def create_post(author: str, content: str) -> bool:
    author, content = author.strip(), content.strip()
    if not author or not content:
        return False
    with _connect() as conn:
        conn.execute(
            "INSERT INTO posts(author, content, created_at) VALUES(?,?,?)",
            (author[:80], content[:4000], datetime.now().strftime("%d/%m/%Y %H:%M")),
        )
        conn.commit()
    return True


class CommunityTab:
    def __init__(self, parent: tk.Widget, robot, market, on_status: Callable[[str], None]) -> None:
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self.frame.pack(fill="both", expand=True)
        self.on_status = on_status
        self._build()
        self.refresh()

    def _build(self) -> None:
        from app.components.banner import TabBanner
        TabBanner(self.frame, "community")
        header = tk.Frame(self.frame, bg=Theme.BG)
        header.pack(fill="x", padx=24, pady=(20, 10))
        tk.Label(header, text="Comunidade", bg=Theme.BG, fg=Theme.TEXT,
                 font=(Theme.FONT_FAMILY, 20, "bold")).pack(side="left")
        tk.Label(header, text="Espaço local para ideias e observações",
                 bg=Theme.BG, fg=Theme.TEXT_SECONDARY,
                 font=(Theme.FONT_FAMILY, 10)).pack(side="left", padx=12)
        SecondaryButton(header, text="Atualizar", command=self.refresh, width=12).pack(side="right")

        composer = Card(self.frame, title="Nova publicação")
        composer.pack(fill="x", padx=24, pady=10)
        row = tk.Frame(composer.body, bg=Theme.CARD)
        row.pack(fill="x")
        tk.Label(row, text="Nome", bg=Theme.CARD, fg=Theme.TEXT_SECONDARY).pack(side="left")
        self.author = tk.Entry(row, width=18)
        self.author.insert(0, "Trader")
        self.author.pack(side="left", padx=8)
        self.content = tk.Entry(row)
        self.content.pack(side="left", fill="x", expand=True, padx=8)
        PrimaryButton(row, text="Publicar", command=self.publish, width=12).pack(side="right")

        feed = Card(self.frame, title="Feed")
        feed.pack(fill="both", expand=True, padx=24, pady=10)
        self.feed = tk.Text(feed.body, bg=Theme.CARD, fg=Theme.TEXT, relief="flat",
                            wrap="word", state="disabled", font=(Theme.FONT_FAMILY, 10))
        self.feed.pack(fill="both", expand=True)

    def refresh(self) -> None:
        try:
            posts = list_posts()
            self.feed.configure(state="normal")
            self.feed.delete("1.0", "end")
            for author, content, created in posts:
                self.feed.insert("end", f"{author} · {created}\n{content}\n\n")
            self.feed.configure(state="disabled")
            self.on_status(f"Comunidade: {len(posts)} publicação(ões)")
        except Exception as exc:
            self.on_status(f"Erro na comunidade: {exc}")

    def publish(self) -> None:
        if not create_post(self.author.get(), self.content.get()):
            messagebox.showwarning("Comunidade", "Informe nome e conteúdo.")
            return
        self.content.delete(0, "end")
        self.refresh()
