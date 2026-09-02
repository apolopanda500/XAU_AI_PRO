# -*- coding: utf-8 -*-
"""Opcoes de CPU do XAU_AI_PRO (Windows).

Permite controlar a intensidade de uso de CPU do processo do app:
  - prioridade de execucao (baixa / normal / alta);
  - afinidade (quais nucleos logicos o processo pode usar);
  - diagnostico (nucleos logicos, mascara atual, % de uso do sistema).

Implementado sem dependencias externas (psutil etc.): usa apenas a API
nativa do Windows via ctypes, mantendo o EXE enxuto.
"""
from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes

# --- Constantes Win32 -----------------------------------------------------
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_INFORMATION = 0x0200

IDLE_PRIORITY_CLASS = 0x00000040          # Baixa (Idle)
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000  # Abaixo do normal
NORMAL_PRIORITY_CLASS = 0x00000020        # Normal
ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000  # Acima do normal
HIGH_PRIORITY_CLASS = 0x00000080          # Alta

_PRIORITY_INDEX = {
    "baixa": 0, "low": 0, "idle": 0,
    "normal": 1, "media": 1, "medium": 1,
    "alta": 2, "high": 2,
}
_PRIORITY_CLASSES = [
    IDLE_PRIORITY_CLASS,
    NORMAL_PRIORITY_CLASS,
    HIGH_PRIORITY_CLASS,
]
_PRIORITY_LABELS = ["Baixa (Idle)", "Normal", "Alta (High)"]


class _SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture", wintypes.WORD),
        ("wReserved", wintypes.WORD),
        ("dwPageSize", wintypes.DWORD),
        ("lpMinimumApplicationAddress", ctypes.c_void_p),
        ("lpMaximumApplicationAddress", ctypes.c_void_p),
        ("dwActiveProcessorMask", ctypes.c_size_t),
        ("dwNumberOfProcessors", wintypes.DWORD),
        ("dwProcessorType", wintypes.DWORD),
        ("dwAllocationGranularity", wintypes.DWORD),
        ("wProcessorLevel", wintypes.WORD),
        ("wProcessorRevision", wintypes.WORD),
    ]


class _FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


def _kernel32():
    return ctypes.windll.kernel32


def _current_handle():
    """Pseudo-handle do processo atual (nao precisa de CloseHandle)."""
    k32 = _kernel32()
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    return k32.GetCurrentProcess()


def logical_cores() -> int:
    """Numero de nucleos logicos do sistema."""
    try:
        k32 = _kernel32()
        info = _SYSTEM_INFO()
        k32.GetSystemInfo(ctypes.byref(info))
        cores = int(info.dwNumberOfProcessors)
        return cores if cores > 0 else (os.cpu_count() or 1)
    except Exception:
        return os.cpu_count() or 1


# ---------------------------------------------------------------------------
# Prioridade
# ---------------------------------------------------------------------------

def set_priority(level: str) -> bool:
    """Define a classe de prioridade do processo.

    level: 'baixa' | 'normal' | 'alta' (aceita low/medium/high/idle/media).
    Retorna True se aplicado com sucesso.
    """
    idx = _PRIORITY_INDEX.get(str(level).strip().lower())
    if idx is None:
        return False
    try:
        k32 = _kernel32()
        k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.SetPriorityClass.restype = wintypes.BOOL
        return bool(k32.SetPriorityClass(_current_handle(), _PRIORITY_CLASSES[idx]))
    except Exception:
        return False


def current_priority() -> str:
    """Classe de prioridade atual do processo (baixa/normal/alta)."""
    try:
        k32 = _kernel32()
        k32.GetPriorityClass.argtypes = [wintypes.HANDLE]
        k32.GetPriorityClass.restype = wintypes.DWORD
        cls = int(k32.GetPriorityClass(_current_handle()))
    except Exception:
        return "normal"
    if cls in (IDLE_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS):
        return "baixa"
    if cls in (ABOVE_NORMAL_PRIORITY_CLASS, HIGH_PRIORITY_CLASS):
        return "alta"
    return "normal"


# ---------------------------------------------------------------------------
# Uso de CPU do sistema (diagnostico)
# ---------------------------------------------------------------------------

def affinity_mask() -> int:
    """Mascara de afinidade atual do processo (bit i = nucleo i)."""
    try:
        k32 = _kernel32()
        k32.GetProcessAffinityMask.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        k32.GetProcessAffinityMask.restype = wintypes.BOOL
        proc = ctypes.c_size_t(0)
        sys_mask = ctypes.c_size_t(0)
        ok = k32.GetProcessAffinityMask(_current_handle(),
                                        ctypes.byref(proc), ctypes.byref(sys_mask))
        return int(proc.value) if ok else 0
    except Exception:
        return 0


def set_affinity(mask: int) -> bool:
    """Restringe o processo aos nucleos indicados na mascara."""
    if mask <= 0:
        return False
    try:
        k32 = _kernel32()
        k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        k32.SetProcessAffinityMask.restype = wintypes.BOOL
        return bool(k32.SetProcessAffinityMask(_current_handle(), ctypes.c_size_t(mask)))
    except Exception:
        return False


def parse_affinity(text: str) -> int:
    """Converte uma descricao de nucleos em mascara. Retorna 0 se invalido.

    Valores aceitos:
      - presets: 'todos' | 'metade' | 'quarto' | 'um'
      - lista personalizada: '0,2-3' (nucleos 0, 2 e 3)
    """
    n = logical_cores()
    raw = (text or "").strip().lower()
    if not raw:
        raw = "todos"

    # Presets
    if raw in ("todos", "all", "auto", "*"):
        return (1 << n) - 1 if n < 64 else 0xFFFFFFFFFFFFFFFF
    if raw in ("metade", "half"):
        return (1 << max(1, n // 2)) - 1
    if raw in ("quarto", "quarter"):
        return (1 << max(1, n // 4)) - 1
    if raw in ("um", "one", "1"):
        return 1

    # Lista personalizada (ex.: "0,2-3")
    mask = 0
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                lo, hi = int(a.strip()), int(b.strip())
            except ValueError:
                return 0
            if lo < 0 or hi > n - 1 or hi < lo:
                return 0
            for c in range(lo, hi + 1):
                mask |= 1 << c
        else:
            try:
                c = int(part)
            except ValueError:
                return 0
            if c < 0 or c > n - 1:
                return 0
            mask |= 1 << c
    return mask


# ---------------------------------------------------------------------------
# Uso de CPU do sistema (diagnostico)
# ---------------------------------------------------------------------------

def _filetime_value(ft: _FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def cpu_usage(sample_ms: int = 300) -> float:
    """Percentual de uso de CPU do sistema no intervalo da amostra."""
    try:
        k32 = _kernel32()
        idle1, kern1, user1 = _FILETIME(), _FILETIME(), _FILETIME()
        k32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kern1), ctypes.byref(user1))
        time.sleep(max(50, sample_ms) / 1000.0)
        idle2, kern2, user2 = _FILETIME(), _FILETIME(), _FILETIME()
        k32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kern2), ctypes.byref(user2))

        idle = _filetime_value(idle2) - _filetime_value(idle1)
        total = (_filetime_value(kern2) + _filetime_value(user2)) \
            - (_filetime_value(kern1) + _filetime_value(user1))
        busy = total - idle
        return (busy / total * 100.0) if total > 0 else 0.0
    except Exception:
        return -1.0


# ---------------------------------------------------------------------------
# Aplicacao a partir da configuracao
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Memoria (RAM)
# ---------------------------------------------------------------------------

class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def memory_info() -> dict:
    """Total/livre/usado de RAM em MB e percentual de uso."""
    try:
        k32 = _kernel32()
        st = _MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
        k32.GlobalMemoryStatusEx.restype = wintypes.BOOL
        if not k32.GlobalMemoryStatusEx(ctypes.byref(st)):
            raise OSError("GlobalMemoryStatusEx falhou")
        total = st.ullTotalPhys / (1024 * 1024)
        avail = st.ullAvailPhys / (1024 * 1024)
        return {
            "total_mb": int(total),
            "free_mb": int(avail),
            "used_mb": int(total - avail),
            "usage_pct": float(st.dwMemoryLoad),
        }
    except Exception:
        return {"total_mb": 0, "free_mb": 0, "used_mb": 0, "usage_pct": 0.0}


def temperature_c() -> float:
    """Temperatura da CPU em Celsius via WMI (MSAcpi_ThermalZoneTemperature).

    Retorna -1.0 quando indisponivel (desktop sem sensor exposto/permissoes).
    """
    import subprocess  # noqa: PLC0415

    try:
        out = subprocess.run(
            ["wmic", "/namespace:\\\\root\\wmi", "PATH", "MSAcpi_ThermalZoneTemperature",
             "get", "CurrentTemperature", "/value"],
            capture_output=True, text=True, timeout=5,
        )
        for line in (out.stdout or "").splitlines():
            if "CurrentTemperature=" in line:
                raw = line.split("=", 1)[1].strip()
                kelvin10 = int(raw)  # decimos de Kelvin
                return round(kelvin10 / 10.0 - 273.15, 1)
        return -1.0
    except Exception:
        return -1.0


# ---------------------------------------------------------------------------
# Limites para treinamento/inferencia de modelos
# ---------------------------------------------------------------------------

def model_n_jobs(config: object) -> int:
    """Numero de nucleos usados pelos modelos (n_jobs).

    Le 'cpu.model_cores': 'auto'|'todos' -> todos os nucleos; numero -> minimo
    (numero, nucleos). Default: todos.
    """
    cores = logical_cores()
    if cores <= 0:
        return -1
    getter = getattr(config, "get", None)
    val = "auto"
    if getter is not None:
        val = str(getter("cpu", "model_cores", default="auto") or "auto").strip().lower()
    if val in ("auto", "todos", "all", "", "0", "-1"):
        return cores
    try:
        n = int(val)
    except ValueError:
        return cores
    if n <= 0:
        return cores
    return max(1, min(n, cores))


def model_max_ram_mb(config: object) -> int:
    """Limite de RAM (MB) para modelos: percentual da RAM total (cpu.max_ram_pct)."""
    info = memory_info()
    total_mb = info.get("total_mb", 0) or 4096
    getter = getattr(config, "get", None)
    pct = 80.0
    if getter is not None:
        try:
            pct = float(getter("cpu", "max_ram_pct", default=80.0) or 80.0)
        except (TypeError, ValueError):
            pct = 80.0
    pct = max(10.0, min(95.0, pct))
    return int(total_mb * pct / 100.0)


def apply_model_limits(config: object) -> tuple[int, int]:
    """Aplica limites de recursos para modelos e retorna (n_jobs, max_ram_mb).

    Define variaveis de ambiente respeitadas pelo pipeline de ML
    (n_jobs, threads numericas e limite de RAM):
      XAU_AI_PRO_N_JOBS, OMP_NUM_THREADS, MKL_NUM_THREADS,
      OPENBLAS_NUM_THREADS, XAU_AI_PRO_MAX_RAM_MB.
    """
    n_jobs = model_n_jobs(config)
    max_ram = model_max_ram_mb(config)
    if n_jobs > 0:
        os.environ["XAU_AI_PRO_N_JOBS"] = str(n_jobs)
        os.environ["OMP_NUM_THREADS"] = str(n_jobs)
        os.environ["MKL_NUM_THREADS"] = str(n_jobs)
        os.environ["OPENBLAS_NUM_THREADS"] = str(n_jobs)
    if max_ram > 0:
        os.environ["XAU_AI_PRO_MAX_RAM_MB"] = str(max_ram)
    return n_jobs, max_ram


def apply_cpu_options(config: object) -> tuple[bool, bool]:
    """Aplica prioridade e afinidade definidas na config do app.

    Retorna (ok_prioridade, ok_afinidade).
    """
    priority = "normal"
    affinity = "todos"
    getter = getattr(config, "get", None)
    if getter is not None:
        priority = getter("cpu", "priority", default="normal") or "normal"
        affinity = getter("cpu", "affinity", default="todos") or "todos"

    ok_p = set_priority(priority)
    mask = parse_affinity(affinity)
    ok_a = bool(mask) and set_affinity(mask)
    return ok_p, ok_a


def describe(priority: str = "", affinity: str = "") -> str:
    """Resumo legivel das opcoes (para logs/status)."""
    out = []
    if priority:
        idx = _PRIORITY_INDEX.get(str(priority).strip().lower())
        out.append(f"prioridade={_PRIORITY_LABELS[idx] if idx is not None else priority}")
    if affinity:
        mask = parse_affinity(affinity)
        out.append(f"afinidade=0x{mask:0X}" if mask else f"afinidade(invalida)={affinity}")
    return " | ".join(out) or "-"


# ---------------------------------------------------------------------------
# Specs da maquina (hardware)
# ---------------------------------------------------------------------------

def system_specs() -> dict:
    """Le as especificacoes REAIS da maquina (sem dependencias externas).

    Retorna dict com: cpu_name, cpu_cores_fisicos, cpu_cores_logicos,
    ram_total_mb, ram_free_mb, disco_total_gb, disco_livre_gb, os_name,
    os_version, arquitetura, gpu_name, hostname.
    """
    import platform  # noqa: PLC0415
    import subprocess  # noqa: PLC0415

    specs: dict = {}
    try:
        specs["hostname"] = platform.node() or ""
        specs["os_name"] = platform.system() or ""
        specs["os_version"] = platform.release() or ""
        specs["arquitetura"] = platform.machine() or ""
        specs["python"] = platform.python_version()
    except Exception:
        pass

    # ---- CPU name (registro do Windows) ----
    cpu_name = ""
    try:
        buf = ctypes.create_unicode_buffer(256)
        sz = wintypes.DWORD(256)
        typ = wintypes.DWORD(0)
        key = wintypes.HKEY()
        advapi = ctypes.windll.advapi32
        advapi.RegOpenKeyExW.argtypes = [wintypes.HKEY, wintypes.LPCWSTR, wintypes.DWORD,
                                         wintypes.DWORD, ctypes.POINTER(wintypes.HKEY)]
        advapi.RegOpenKeyExW.restype = wintypes.LONG
        advapi.RegQueryValueExW.argtypes = [wintypes.HKEY, wintypes.LPCWSTR,
                                            ctypes.POINTER(wintypes.DWORD),
                                            ctypes.POINTER(wintypes.DWORD),
                                            ctypes.c_void_p,
                                            ctypes.POINTER(wintypes.DWORD)]
        advapi.RegQueryValueExW.restype = wintypes.LONG
        advapi.RegCloseKey.argtypes = [wintypes.HKEY]
        r = advapi.RegOpenKeyExW(0x80000002,  # HKLM
                                 r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                                 0, 0x20019, ctypes.byref(key))
        if r == 0:
            advapi.RegQueryValueExW(key, "ProcessorNameString", None, ctypes.byref(typ),
                                    buf, ctypes.byref(sz))
            cpu_name = buf.value.strip()
            advapi.RegCloseKey(key)
    except Exception:
        cpu_name = ""
    specs["cpu_name"] = cpu_name or "Desconhecido"

    # ---- Nucleos fisicos/logicos (WMI fallback) ----
    phys, logi = 0, 0
    try:
        out = subprocess.run(
            ["wmic", "cpu", "get", "NumberOfCores,NumberOfLogicalProcessors", "/value"],
            capture_output=True, text=True, timeout=6,
        )
        for line in (out.stdout or "").splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                if k == "NumberOfCores":
                    try:
                        phys = int(v)
                    except ValueError:
                        pass
                elif k == "NumberOfLogicalProcessors":
                    try:
                        logi = int(v)
                    except ValueError:
                        pass
    except Exception:
        pass
    specs["cpu_cores_fisicos"] = phys or logical_cores()
    specs["cpu_cores_logicos"] = logi or logical_cores()

    # ---- RAM / Disco ----
    mem = memory_info()
    specs["ram_total_mb"] = mem.get("total_mb", 0)
    specs["ram_free_mb"] = mem.get("free_mb", 0)
    try:
        free_b, total_b = ctypes.c_ulonglong(0), ctypes.c_ulonglong(0)
        _kernel32().GetDiskFreeSpaceExW("C:\\", None,
                                        ctypes.byref(total_b), ctypes.byref(free_b))
        specs["disco_total_gb"] = round(total_b.value / (1024 ** 3), 1)
        specs["disco_livre_gb"] = round(free_b.value / (1024 ** 3), 1)
    except Exception:
        specs["disco_total_gb"] = -1
        specs["disco_livre_gb"] = -1

    # ---- GPU (via WMI) ----
    gpu = ""
    try:
        out = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "Name", "/value"],
            capture_output=True, text=True, timeout=6,
        )
        for line in (out.stdout or "").splitlines():
            if "=" in line and "Name=" in line:
                gpu = line.partition("=")[2].strip()
                if gpu:
                    break
    except Exception:
        gpu = ""
    specs["gpu_name"] = gpu or "N/A"
    return specs


# ---------------------------------------------------------------------------
# Presets de RAM por modelo (X1=2GB, X2=4GB, ...)
# ---------------------------------------------------------------------------

DEFAULT_MODEL_PRESETS: dict[str, int] = {
    "X1 Lite": 1024,      # 1 GB  - rapido, entrada
    "X1": 2048,           # 2 GB
    "X2": 4096,           # 4 GB
    "X3": 8192,           # 8 GB
    "X4": 12288,          # 12 GB
    "X5 Pro": 16384,      # 16 GB
    "X5 Ultra": 24576,    # 24 GB
}

MODEL_PRESET_ORDER = ["X1 Lite", "X1", "X2", "X3", "X4", "X5 Pro", "X5 Ultra"]


def model_presets(config: object = None) -> dict[str, int]:
    """Presets de RAM (MB) por modelo, vindos da config (cpu.model_presets)."""
    getter = getattr(config, "get", None) if config is not None else None
    if getter is not None:
        try:
            saved = getter("cpu", "model_presets", default={}) or {}
            if saved:
                out = {}
                for k, v in saved.items():
                    try:
                        out[str(k)] = int(v)
                    except (TypeError, ValueError):
                        pass
                if out:
                    return out
        except Exception:
            pass
    return dict(DEFAULT_MODEL_PRESETS)


def current_model_preset(config: object) -> str:
    """Nome do preset ativo (cpu.model_preset). Default 'X2'."""
    getter = getattr(config, "get", None)
    if getter is not None:
        try:
            name = str(getter("cpu", "model_preset", default="X2") or "X2")
            if name in DEFAULT_MODEL_PRESETS:
                return name
        except Exception:
            pass
    return "X2"


def preset_ram_mb(config: object) -> int:
    """RAM (MB) do preset de modelo ativo."""
    name = current_model_preset(config)
    presets = model_presets(config)
    return presets.get(name, 2048)


def set_model_preset(config: object, name: str) -> bool:
    """Ativa um preset de modelo e aplica o limite de RAM."""
    presets = model_presets(config)
    if name not in presets:
        return False
    getter = getattr(config, "set", None)
    if getter is None:
        return False
    getter("cpu", "model_preset", value=name)
    ram_mb = presets[name]
    try:
        t = memory_info().get("total_mb", 4096) or 4096
        getter("cpu", "max_ram_pct", value=min(95.0, max(10.0, ram_mb * 100.0 / t)))
    except Exception:
        pass
    os.environ["XAU_AI_PRO_MAX_RAM_MB"] = str(ram_mb)
    os.environ["XAU_AI_PRO_MODEL_PRESET"] = name
    return True
