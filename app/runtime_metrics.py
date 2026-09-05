from __future__ import annotations

import threading

_lock = threading.Lock()
_gui_fps = 0.0


def set_gui_fps(value: float) -> None:
    global _gui_fps
    with _lock:
        _gui_fps = max(0.0, float(value))


def get_gui_fps() -> float:
    with _lock:
        return _gui_fps
