# -*- coding: utf-8 -*-
"""
Motor de aprendizado continuo diario do XAU_AI_PRO.
Responsavel por agendar treinamento, rotear modelos e sincronizar predicoes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config_manager import get_config
from app.utils.paths import get_base_dir, get_data_dir, get_mql_data_path


LEARNING_HISTORY_FILE = get_data_dir() / "learning_history.json"


def _python_exe() -> str:
    """Retorna um interpretador Python com as dependencias do pipeline
    (numpy + MetaTrader5). Evita usar venv do app (sem numpy)."""
    # 1. Se estiver rodando dentro do .exe (PyInstaller), usa o proprio exe
    #    (o bundle ja contem numpy + MetaTrader5).
    if getattr(sys, "frozen", False):
        return sys.executable or "python"

    candidates = []
    if sys.executable:
        candidates.append(sys.executable)
    # 2. Python do sistema (Python 3.12) instalado localmente
    local_py = Path.home() / "AppData" / "Local" / "Programs" / "Python"
    if local_py.is_dir():
        for ver_dir in sorted(local_py.iterdir(), reverse=True):
            exe = ver_dir / "python.exe"
            if exe.exists():
                candidates.append(str(exe))
    # 3. Fallback: python no PATH
    candidates.append("python")

    for exe in candidates:
        try:
            r = subprocess.run(
                [exe, "-c", "import numpy, MetaTrader5"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if r.returncode == 0:
                return exe
        except Exception:
            continue

    # Ultimo recurso: o atual (vai falhar com mensagem clara)
    return sys.executable or "python"


class LearningEngine:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_status: dict[str, Any] = {"state": "idle"}
        self._lock = threading.Lock()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._last_status)

    def _update_status(self, **kwargs: Any) -> None:
        with self._lock:
            self._last_status.update(kwargs)
            self._last_status["updated_at"] = datetime.now().isoformat()

    def _load_history(self) -> dict[str, Any]:
        if not LEARNING_HISTORY_FILE.exists():
            return {"runs": [], "best_model": None}
        try:
            return json.loads(LEARNING_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"runs": [], "best_model": None}

    def _save_history(self, history: dict[str, Any]) -> None:
        LEARNING_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        LEARNING_HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

    def _add_run(self, result: dict[str, Any]) -> None:
        history = self._load_history()
        history["runs"].append(result)
        history["runs"] = history["runs"][-50:]
        best = None
        for run in history["runs"]:
            if run.get("ok") and (best is None or run.get("score", 0) > best.get("score", 0)):
                best = run
        history["best_model"] = best
        self._save_history(history)

    def run_training(self) -> dict[str, Any]:
        self._update_status(state="training", message="Treinamento iniciado")
        py_dir = get_base_dir() / "Python"
        main_script = py_dir / "main.py"
        if not main_script.exists():
            result = {"ok": False, "error": "main.py nao encontrado", "time": datetime.now().isoformat()}
            self._update_status(state="error", message=result["error"])
            return result
        try:
            proc = subprocess.run(
                [_python_exe(), str(main_script), "train"],
                cwd=str(py_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )
            success = proc.returncode == 0
            result = {
                "ok": success,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "time": datetime.now().isoformat(),
                "score": 0.0,
            }
            if success:
                self._update_status(state="idle", message="Treinamento concluido")
            else:
                self._update_status(state="error", message=f"Erro treinamento: {proc.returncode}")
            self._add_run(result)
            return result
        except subprocess.TimeoutExpired:
            result = {"ok": False, "error": "Timeout no treinamento", "time": datetime.now().isoformat()}
            self._update_status(state="error", message=result["error"])
            self._add_run(result)
            return result
        except Exception as e:
            result = {"ok": False, "error": str(e), "time": datetime.now().isoformat()}
            self._update_status(state="error", message=str(e))
            self._add_run(result)
            return result

    def run_prediction(self) -> dict[str, Any]:
        self._update_status(state="predicting", message="Gerando predicoes")
        py_dir = get_base_dir() / "Python"
        main_script = py_dir / "main.py"
        if not main_script.exists():
            return {"ok": False, "error": "main.py nao encontrado"}
        try:
            proc = subprocess.run(
                [_python_exe(), str(main_script), "predict"],
                cwd=str(py_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            result = {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "time": datetime.now().isoformat(),
            }
            if result["ok"]:
                result["sync"] = self.sync_predictions()
                self._update_status(state="idle", message="Predicoes sincronizadas")
            else:
                self._update_status(state="error", message=f"Erro predicao: {proc.returncode}")
            return result
        except Exception as e:
            self._update_status(state="error", message=str(e))
            return {"ok": False, "error": str(e)}

    def full_cycle(self) -> dict[str, Any]:
        train = self.run_training()
        if not train.get("ok"):
            return {"ok": False, "stage": "train", "detail": train}
        predict = self.run_prediction()
        return {"ok": predict.get("ok"), "stage": "complete", "train": train, "predict": predict}

    def sync_predictions(self) -> dict[str, Any]:
        try:
            src_dir = get_base_dir() / "Python" / "ai"
            dst_dir = get_mql_data_path()
            dst_dir.mkdir(parents=True, exist_ok=True)
            copied = 0
            for src in src_dir.glob("prediction*.json"):
                shutil.copy2(src, dst_dir / src.name)
                copied += 1
            return {"ok": True, "copied": copied}
        except Exception as e:
            return {"ok": False, "error": str(e)}


    def download_models(self, symbols=None, timeframes=None) -> dict[str, Any]:
        """Baixa modelos sob demanda (estrategia thin-installer).

        Roda Python/model_manager.py via subprocess (consistente com o resto
        do engine) e reporta como run no historico.
        """
        self._update_status(state="downloading", message="Baixando modelos...")
        py_dir = get_base_dir() / "Python"
        script = py_dir / "model_manager.py"
        if not script.exists():
            result = {"ok": False, "error": "model_manager.py nao encontrado", "time": datetime.now().isoformat()}
            self._update_status(state="error", message=result["error"])
            return result
        symbols = [s.upper() for s in (symbols or ["XAUUSD"])]
        timeframes = [(t.upper() if isinstance(t, str) else t) for t in (timeframes or ["M5"])]
        args = [_python_exe(), str(script), "--symbols", ",".join(symbols), "--timeframes", ",".join(timeframes)]
        try:
            proc = subprocess.run(
                args,
                cwd=str(py_dir),
                capture_output=True,
                text=True,
                timeout=1800,
            )
            ok = proc.returncode == 0
            result = {
                "ok": ok,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-2000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "time": datetime.now().isoformat(),
                "stage": "download_models",
                "score": 0.0,
            }
            if ok:
                self._update_status(state="idle", message="Modelos baixados")
            else:
                self._update_status(state="error", message=f"Erro download: {proc.returncode}")
            self._add_run(result)
            return result
        except Exception as e:
            result = {"ok": False, "error": str(e), "time": datetime.now().isoformat()}
            self._update_status(state="error", message=str(e))
            self._add_run(result)
            return result

    def start_scheduler(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._update_status(state="scheduled", message="Agendador iniciado")

    def stop_scheduler(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._update_status(state="stopped", message="Agendador parado")

    def _loop(self) -> None:
        cfg = get_config()
        daily_time = cfg.get("learning", "daily_time", default="02:00")
        interval = int(cfg.get("learning", "interval_minutes", default=60))
        last_daily_check = ""
        last_interval_minute = -1
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                time_str = now.strftime("%H:%M")
                if time_str == daily_time and time_str != last_daily_check:
                    last_daily_check = time_str
                    self._update_status(state="daily_training", message="Treinamento diario disparado")
                    self.full_cycle()
                if interval > 0 and now.minute % interval == 0 and now.minute != last_interval_minute and now.second < 10:
                    last_interval_minute = now.minute
                    self._update_status(state="incremental", message="Treinamento incremental")
                    self.full_cycle()
                if time_str != daily_time:
                    last_daily_check = ""
                time.sleep(5)
            except Exception as e:
                self._update_status(state="error", message=str(e))
                time.sleep(30)


_learning_engine: LearningEngine | None = None


def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine

