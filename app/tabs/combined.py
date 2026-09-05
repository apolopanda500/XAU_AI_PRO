from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from app.theme.mexc import Theme


class CombinedTab:
    """Agrupa telas relacionadas e instancia cada uma somente ao ser aberta."""

    def __init__(self, parent, sections: list[tuple[str, Callable[[tk.Widget], Any]]]) -> None:
        self.frame = tk.Frame(parent, bg=Theme.BG)
        self._sections = dict(sections)
        self._instances: dict[str, Any] = {}
        self._active = ""
        self._buttons: dict[str, tk.Button] = {}

        navigation = tk.Frame(self.frame, bg=Theme.BG)
        navigation.pack(fill="x", padx=24, pady=(8, 4))
        for label, _factory in sections:
            button = tk.Button(
                navigation,
                text=label,
                command=lambda name=label: self.show(name),
                bg=Theme.PANEL,
                fg=Theme.TEXT_SECONDARY,
                activebackground=Theme.CARD_HOVER,
                activeforeground=Theme.TEXT,
                relief="flat",
                borderwidth=0,
                padx=14,
                pady=7,
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 6))
            self._buttons[label] = button

        self.content = tk.Frame(self.frame, bg=Theme.BG)
        self.content.pack(fill="both", expand=True)
        self.show(sections[0][0])

    def show(self, label: str) -> None:
        if label not in self._sections:
            return
        if self._active in self._instances:
            self._instances[self._active].frame.pack_forget()
        if label not in self._instances:
            self._instances[label] = self._sections[label](self.content)
        self._active = label
        self._instances[label].frame.pack(fill="both", expand=True)
        for name, button in self._buttons.items():
            button.configure(
                bg=Theme.CARD if name == label else Theme.PANEL,
                fg=Theme.PRIMARY if name == label else Theme.TEXT_SECONDARY,
            )
        instance = self._instances[label]
        if hasattr(instance, "refresh"):
            instance.refresh()
        if hasattr(instance, "refresh_now"):
            instance.refresh_now()
        if hasattr(instance, "start_auto"):
            instance.start_auto()

    def refresh(self) -> None:
        instance = self._instances.get(self._active)
        if instance is not None and hasattr(instance, "refresh"):
            instance.refresh()
        elif instance is not None and hasattr(instance, "refresh_now"):
            instance.refresh_now()

    def check_ea(self) -> None:
        instance = self._instances.get(self._active)
        if instance is not None and hasattr(instance, "check_ea"):
            instance.check_ea()

    def __getattr__(self, name: str):
        if name.startswith("stop_") or name == "start_monitor":
            def relay(*args, **kwargs) -> None:
                for instance in self._instances.values():
                    method = getattr(instance, name, None)
                    if method:
                        method(*args, **kwargs)
            return relay
        raise AttributeError(name)
