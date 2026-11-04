#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""MT5 ASSISTANT MCP — servidor MCP local (stdio) para o XAU_AI_PRO.

PORQUE EXISTE
  O MCP da MetaQuotes expõe ficheiros, compilação e o terminal, mas NÃO
  executa programas .ex5 nem corre o pipeline Python. Hoje isso é feito
  pelo shell com `cd /d ... && set ... && python.exe ...`, que o cmd.exe
  trunca em comandos multi-linha.

  Este servidor dá ao assistente três ferramentas pequenas e auditáveis:
    - roots_info      : quais pastas este servidor aceita (raízes fixas)
    - pipeline_run    : corre xau_model_tools.py com um COMANDO PERMITIDO
    - dataset_info    : mede o dataset CSV (linhas, símbolos, 1º/último bar)
    - prediction_get  : devolve o JSON de predição de um símbolo
    - validate_report : devolve o resumo de json_validation_report.json

RAÍZES (fixas no código, não vêm do cliente)
  read  : MQL5 (tudo), em particular MQL5\Files\Data e MQL5\Files\XAU_AI_PRO
  write : só o pipeline (publish/regen/train) escreve em MQL5\Files\Data
  exec  : só o interpretador Python e o xau_model_tools.py

SEGURANÇA
  - Nada de shell=True: subprocess com lista de argumentos.
  - `pipeline_run` aceita apenas a lista ALLOWED_COMMANDS; qualquer outro
    valor é recusado com motivo.
  - `prediction_get` valida o símbolo por regex e resolve o caminho DENTRO
    de Data; nada de `..`, barras ou caminhos absolutos.
  - Não há ferramenta que coloque, altere ou cancele ordens. Este servidor
    nunca negocia.
  - Transporte stdio, uma mensagem JSON por linha (MCP 2024-11-05).

TESTE
  python mt5_assistant_mcp.py --selftest
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
# ...\MQL5\Files\XAU_AI_PRO\Mcp\mt5_assistant_mcp.py
MQL5_DIR = HERE.parents[3]
FILES_DIR = MQL5_DIR / "Files"
DATA_DIR = FILES_DIR / "Data"
PROJECT_DIR = FILES_DIR / "XAU_AI_PRO"
PY_DIR = PROJECT_DIR / "Python"
TOOL_PY = PY_DIR / "xau_model_tools.py"
TOOLS_DIR = PROJECT_DIR / "Tools"
AUDIT_PY = TOOLS_DIR / "audit_project.py"
SCAFFOLD_PY = TOOLS_DIR / "new_mq5_project.py"
PY_EXE = Path(r"C:\Users\Micro\AppData\Local\Programs\Python\Python312-embed\python.exe")
GIT_EXE = Path(r"C:\Program Files\Git\bin\git.exe")
REPORT = DATA_DIR / "json_validation_report.json"

PROTOCOL = "2024-11-05"
SERVER_NAME = "mt5_assistant"
SERVER_VERSION = "1.2.0"

ALLOWED_COMMANDS = ("validate", "publish", "regen", "probe", "stamp", "train")
SYMBOL_RE = re.compile(r"^[A-Za-z0-9#._]{1,32}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9#._\-/\\]{1,200}$")
MAX_TEXT = 200_000

# Pastas onde escrita é permitida (apenas dentro do projeto XAU_AI_PRO)
WRITE_ROOTS = [PROJECT_DIR]

# Raízes extras de leitura (configuráveis via roots.json)
ROOTS_FILE = HERE.parent / "roots.json"


def load_extra_roots():
    if ROOTS_FILE.exists():
        try:
            data = json.loads(ROOTS_FILE.read_text(encoding="utf-8"))
            return [Path(p) for p in data.get("read_roots", [])]
        except Exception:
            return []
    return []


def save_extra_roots(roots):
    ROOTS_FILE.write_text(json.dumps({"read_roots": [str(r) for r in roots]}, indent=2), encoding="utf-8")


EXTRA_READ_ROOTS = load_extra_roots()


def all_read_roots():
    roots = [MQL5_DIR.resolve()] + [r.resolve() for r in EXTRA_READ_ROOTS if r.exists()]
    return roots


class ToolError(Exception):
    """Erro devolvido ao cliente como isError=true, com motivo legível."""


# ----------------------------------------------------------------------
# Raízes e guardas de caminho
# ----------------------------------------------------------------------
def roots():
    return {
        "read_roots": [str(MQL5_DIR)],
        "write_roots": [],
        "execute_roots": [str(PY_DIR), str(PY_EXE)],
        "notes": [
            "Este servidor só lê. A escrita acontece apenas dentro de "
            "xau_model_tools.py (publish/regen/train) em MQL5\\Files\\Data.",
            "Nenhuma ferramenta coloca, altera ou cancela ordens.",
        ],
    }


def safe_data_file(name: str) -> Path:
    if not SYMBOL_RE.match(name):
        raise ToolError(f"nome recusado: {name!r} (permitido: A-Z a-z 0-9 # . _)")
    path = (DATA_DIR / name).resolve()
    if DATA_DIR.resolve() not in path.parents:
        raise ToolError("caminho fora de MQL5\\Files\\Data")
    return path


def safe_read_path(rel: str) -> Path:
    rel = (rel or "").strip()
    if not rel:
        raise ToolError("caminho vazio")
    # se for caminho absoluto, validar contra roots
    if Path(rel).is_absolute():
        path = Path(rel).resolve()
    else:
        # tentar relativo a cada root
        path = None
        for root in all_read_roots():
            cand = (root / rel).resolve()
            if cand.exists():
                path = cand
                break
        if path is None:
            path = (MQL5_DIR / rel).resolve()
    # validar dentro de alguma root
    for root in all_read_roots():
        try:
            path.relative_to(root)
            ok = True
            break
        except ValueError:
            ok = False
    if not ok:
        raise ToolError(f"caminho fora das raizes permitidas: {path}")
    if not path.exists():
        raise ToolError(f"nao existe: {path}")
    return path


def safe_write_path(rel: str) -> Path:
    rel = (rel or "").strip()
    if not rel:
        raise ToolError("caminho vazio")
    rel = rel.replace("/", "\\")
    if ".." in rel.split("\\"):
        raise ToolError("caminho com '..' recusado")
    base = PROJECT_DIR.resolve()
    path = (base / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
    try:
        path.relative_to(base)
    except ValueError:
        raise ToolError(f"escrita fora do projeto XAU_AI_PRO: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_cmd(args, cwd=None, timeout=300):
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"timeout de {timeout}s")
    except FileNotFoundError as exc:
        raise ToolError(f"executavel ausente: {exc}")
    out = clip(proc.stdout.strip())
    err = clip(proc.stderr.strip())
    parts = [f"exit={proc.returncode}"]
    if out:
        parts += ["--- stdout ---", out]
    if err:
        parts += ["--- stderr ---", err]
    return "\n".join(parts)


def clip(text: str) -> str:
    text = text or ""
    if len(text) > MAX_TEXT:
        return text[:MAX_TEXT] + f"\n[... truncado em {MAX_TEXT} caracteres]"
    return text


# ----------------------------------------------------------------------
# Ferramentas
# ----------------------------------------------------------------------
def tool_roots_info(_args):
    info = roots()
    info["dataset_primary_exists"] = (DATA_DIR / "dataset_mt5_20261101.csv").exists()
    info["tool_py_exists"] = TOOL_PY.exists()
    info["python_exists"] = PY_EXE.exists()
    return json.dumps(info, indent=2, ensure_ascii=False)


def tool_pipeline_run(args):
    command = str(args.get("command", "")).strip()
    if command not in ALLOWED_COMMANDS:
        raise ToolError(
            "comando recusado: "
            + repr(command)
            + " | permitidos: "
            + ", ".join(ALLOWED_COMMANDS)
        )
    if not TOOL_PY.exists():
        raise ToolError(f"nao encontrado: {TOOL_PY}")
    if not PY_EXE.exists():
        raise ToolError(f"interpretador ausente: {PY_EXE}")

    timeout = int(args.get("timeout_sec", 1800))
    timeout = max(30, min(timeout, 7200))

    started = time.time()
    try:
        proc = subprocess.run(
            [str(PY_EXE), str(TOOL_PY), command],
            cwd=str(PY_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"timeout de {timeout}s a correr '{command}'")

    elapsed = round(time.time() - started, 2)
    out = clip(proc.stdout.strip())
    err = clip(proc.stderr.strip())
    parts = [
        f"[pipeline] command={command} exit={proc.returncode} elapsed={elapsed}s",
        "--- stdout ---",
        out if out else "(vazio)",
    ]
    if err:
        parts += ["--- stderr ---", err]
    return "\n".join(parts)


def tool_dataset_info(args):
    name = str(args.get("file", "dataset_mt5_20261101.csv"))
    path = safe_data_file(name)
    if not path.exists():
        raise ToolError(f"dataset ausente: {path.name}")

    rows = 0
    symbols = {}
    first = None
    last = None
    bad = 0
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.count(",") < 7:
                bad += 1
                continue
            p = line.rstrip().split(",")
            rows += 1
            symbols[p[1]] = symbols.get(p[1], 0) + 1
            if first is None:
                first = p[0]
            last = p[0]

    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))
    return json.dumps(
        {
            "file": path.name,
            "mtime_local": mtime,
            "linhas": rows,
            "linhas_malformadas": bad,
            "simbolos": len(symbols),
            "barras_por_simbolo": symbols,
            "primeiro_bar": first,
            "ultimo_bar": last,
        },
        indent=2,
        ensure_ascii=False,
    )


def tool_prediction_get(args):
    symbol = str(args.get("symbol", "")).strip()
    if not symbol:
        raise ToolError("symbol vazio: símbolo vazio é recusa com motivo, nunca um ativo padrão")
    tf = str(args.get("timeframe", "")).strip().upper()
    name = f"prediction_{symbol}{('_' + tf) if tf else ''}.json"
    path = safe_data_file(name)
    if not path.exists():
        alt = safe_data_file(f"prediction_{symbol}.json")
        if not alt.exists():
            raise ToolError(f"sem predição: {name}")
        path = alt
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(f"JSON invalido em {path.name}: {exc}")
    resumo = {
        "file": path.name,
        "symbol": payload.get("symbol"),
        "signal": payload.get("signal"),
        "confidence": payload.get("confidence"),
        "model": payload.get("model"),
        "timeframe": payload.get("timeframe"),
        "timestamp_utc": payload.get("timestamp_utc"),
        "publicable": payload.get("publicable"),
    }
    return json.dumps(resumo, indent=2, ensure_ascii=False)


def tool_validate_report(_args):
    if not REPORT.exists():
        raise ToolError(f"relatorio ausente: {REPORT.name}")
    raw = REPORT.read_text(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(f"relatorio invalido: {exc}")
    if isinstance(payload, dict):
        resumo = {k: payload[k] for k in ("generated_utc", "total", "ok", "errors", "warnings") if k in payload}
        erros = payload.get("errors") or []
        avisos = payload.get("warnings") or []
        resumo["errors_count"] = len(erros)
        resumo["warnings_count"] = len(avisos)
        resumo["primeiros_avisos"] = avisos[:10]
        return json.dumps(resumo, indent=2, ensure_ascii=False)
    return clip(raw)


def tool_git_status(_args):
    if not GIT_EXE.exists():
        raise ToolError(f"git ausente: {GIT_EXE}")
    cwd = PROJECT_DIR
    branch = run_cmd([str(GIT_EXE), "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, timeout=60)
    status = run_cmd([str(GIT_EXE), "status", "--short"], cwd=cwd, timeout=60)
    return f"[git] branch:\n{branch}\n\n[git] status --short:\n{status}"


def tool_git_diff(args):
    if not GIT_EXE.exists():
        raise ToolError(f"git ausente: {GIT_EXE}")
    cwd = PROJECT_DIR
    staged = bool(args.get("staged", False))
    path = args.get("path")
    cmd = [str(GIT_EXE), "diff"]
    if staged:
        cmd.append("--staged")
    if path:
        cmd += ["--", str(path)]
    return run_cmd(cmd, cwd=cwd, timeout=120)


def tool_git_log(args):
    if not GIT_EXE.exists():
        raise ToolError(f"git ausente: {GIT_EXE}")
    cwd = PROJECT_DIR
    n = int(args.get("n", 15))
    n = max(1, min(n, 100))
    return run_cmd([str(GIT_EXE), "log", "--oneline", f"-{n}"], cwd=cwd, timeout=60)


def tool_run_tests(args):
    path = args.get("path")
    marker = args.get("marker")
    extra = args.get("extra", "")
    cmd = [str(PY_EXE), "-m", "pytest", "-q"]
    if marker:
        cmd += ["-m", str(marker)]
    if path:
        cmd.append(str(path))
    if extra:
        cmd += str(extra).split()
    cwd = PROJECT_DIR
    return run_cmd(cmd, cwd=cwd, timeout=int(args.get("timeout_sec", 600)))


def tool_run_lint(args):
    target = args.get("path", "Python")
    if Path(target).is_absolute():
        target_path = Path(target)
    else:
        target_path = (PROJECT_DIR / target).resolve()
    if not target_path.exists():
        raise ToolError(f"nao existe: {target_path}")
    return run_cmd([str(PY_EXE), "-m", "flake8", str(target_path), "--max-line-length=120"], cwd=PROJECT_DIR, timeout=300)


def tool_file_read(args):
    rel = args.get("path")
    if not rel:
        raise ToolError("path obrigatório")
    p = safe_read_path(rel)
    if p.is_dir():
        raise ToolError(f"é diretório: {p}")
    start = args.get("start_line")
    end = args.get("end_line")
    text = p.read_text(encoding="utf-8", errors="replace")
    if start or end:
        lines = text.splitlines()
        s = (int(start) - 1) if start else 0
        e = int(end) if end else len(lines)
        s = max(0, s)
        e = min(len(lines), e)
        text = "\n".join(lines[s:e])
    return clip(text)


def tool_file_write(args):
    rel = args.get("path")
    content = args.get("content")
    if not rel:
        raise ToolError("path obrigatório")
    if content is None:
        raise ToolError("content obrigatório")
    p = safe_write_path(rel)
    # backup se existir
    if p.exists():
        backup = p.with_suffix(p.suffix + ".bak")
        try:
            backup.write_text(p.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        except Exception:
            pass
    p.write_text(str(content), encoding="utf-8")
    return json.dumps({"written": str(p), "bytes": len(str(content))}, ensure_ascii=False)


def tool_list_dir(args):
    rel = args.get("path", ".")
    p = safe_read_path(rel)
    if not p.is_dir():
        raise ToolError(f"nao é diretório: {p}")
    depth = int(args.get("depth", 2))
    depth = max(1, min(depth, 6))
    out = []
    base = p
    for root, dirs, files in os.walk(base):
        level = len(Path(root).relative_to(base).parts)
        if level >= depth:
            dirs[:] = []
        for d in sorted(dirs):
            out.append("D " + str(Path(root, d).relative_to(MQL5_DIR)))
        for f in sorted(files):
            out.append("F " + str(Path(root, f).relative_to(MQL5_DIR)))
    return "\n".join(out[:500])


def tool_search_text(args):
    query = args.get("query")
    if not query:
        raise ToolError("query obrigatório")
    root_rel = args.get("path", "Files\\XAU_AI_PRO")
    root = safe_read_path(root_rel)
    glob_pat = args.get("glob", "*")
    matches = []
    for p in root.rglob(glob_pat):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if query.lower() in line.lower():
                matches.append(f"{p.relative_to(MQL5_DIR)}:{i}: {line.strip()[:200]}")
                if len(matches) >= 200:
                    break
        if len(matches) >= 200:
            break
    return "\n".join(matches) if matches else "(sem resultados)"


def tool_list_roots(_args):
    roots = all_read_roots()
    return json.dumps({"read_roots": [str(r) for r in roots], "write_roots": [str(r) for r in WRITE_ROOTS]}, indent=2, ensure_ascii=False)


def tool_add_read_root(args):
    path = args.get("path")
    if not path:
        raise ToolError("path obrigatório")
    p = Path(path).resolve()
    if not p.exists() or not p.is_dir():
        raise ToolError(f"pasta inexistente: {p}")
    global EXTRA_READ_ROOTS
    if p not in EXTRA_READ_ROOTS:
        EXTRA_READ_ROOTS.append(p)
        save_extra_roots(EXTRA_READ_ROOTS)
    return json.dumps({"added": str(p), "read_roots": [str(r) for r in all_read_roots()]}, ensure_ascii=False)


def tool_remove_read_root(args):
    path = args.get("path")
    if not path:
        raise ToolError("path obrigatório")
    p = Path(path).resolve()
    global EXTRA_READ_ROOTS
    EXTRA_READ_ROOTS = [r for r in EXTRA_READ_ROOTS if r.resolve() != p]
    save_extra_roots(EXTRA_READ_ROOTS)
    return json.dumps({"removed": str(p), "read_roots": [str(r) for r in all_read_roots()]}, ensure_ascii=False)


ALLOWED_EXECUTABLES = {
    "python": str(PY_EXE),
    "git": str(GIT_EXE),
    "node": "node",
    "npm": "npm",
    "pip": str(PY_EXE),
    "metaeditor": r"C:\Program Files\MetaTrader 5\metaeditor64.exe",
    "flake8": str(PY_EXE),
    "pytest": str(PY_EXE),
}


def tool_run_command(args):
    exe_key = args.get("executable", "")
    if exe_key not in ALLOWED_EXECUTABLES:
        raise ToolError(f"executavel nao permitido: {exe_key} | permitidos: {', '.join(ALLOWED_EXECUTABLES)}")
    cmd = [ALLOWED_EXECUTABLES[exe_key]]
    if exe_key == "pip":
        cmd += ["-m", "pip"]
    elif exe_key == "flake8":
        cmd += ["-m", "flake8"]
    elif exe_key == "pytest":
        cmd += ["-m", "pytest"]
    extra_args = args.get("args", [])
    if isinstance(extra_args, str):
        extra_args = extra_args.split()
    cmd += list(extra_args)
    cwd = args.get("cwd")
    if cwd:
        cwd = safe_read_path(cwd)
    timeout = int(args.get("timeout_sec", 300))
    timeout = max(30, min(timeout, 3600))
    return run_cmd(cmd, cwd=cwd, timeout=timeout)


def tool_npm_run(args):
    script = args.get("script", "build")
    cwd = args.get("cwd", "frontend")
    cwd_path = safe_read_path(cwd)
    return run_cmd(["npm", "run", str(script)], cwd=cwd_path, timeout=int(args.get("timeout_sec", 600)))


def tool_metaeditor_compile(args):
    file_rel = args.get("file")
    if not file_rel:
        raise ToolError("file obrigatório")
    p = safe_read_path(file_rel)
    me = Path(ALLOWED_EXECUTABLES["metaeditor"])
    if not me.exists():
        raise ToolError(f"metaeditor ausente: {me}")
    cmd = [str(me), f"/compile:{p}", "/log"]
    defines = args.get("defines")
    if defines:
        cmd.append(f"/define:{defines}")
    include = args.get("include")
    if include:
        cmd.append(f"/include:{include}")
    return run_cmd(cmd, cwd=p.parent, timeout=int(args.get("timeout_sec", 300)))


def tool_project_info(_args):
    info = {
        "project_dir": str(PROJECT_DIR),
        "mql5_dir": str(MQL5_DIR),
        "python": str(PY_EXE),
        "git": str(GIT_EXE),
        "git_exists": GIT_EXE.exists(),
        "python_exists": PY_EXE.exists(),
        "project_exists": PROJECT_DIR.exists(),
        "tests_dir_exists": (PROJECT_DIR / "tests").exists(),
        "read_roots": [str(r) for r in all_read_roots()],
    }
    return json.dumps(info, indent=2, ensure_ascii=False)


def tool_create_folder(args):
    rel = args.get("path")
    if not rel:
        raise ToolError("path obrigatório")
    if Path(rel).is_absolute():
        p = Path(rel).resolve()
    else:
        p = (PROJECT_DIR / rel).resolve()
    ok = False
    for w in WRITE_ROOTS:
        try:
            p.relative_to(w.resolve())
            ok = True
            break
        except ValueError:
            continue
    if not ok:
        raise ToolError(f"criacao fora das raizes de escrita: {p}")
    p.mkdir(parents=True, exist_ok=True)
    return json.dumps({"created": str(p)}, ensure_ascii=False)


def tool_delete_file(args):
    rel = args.get("path")
    if not rel:
        raise ToolError("path obrigatório")
    if Path(rel).is_absolute():
        p = Path(rel).resolve()
    else:
        p = safe_write_path(rel)
    ok = False
    for w in WRITE_ROOTS:
        try:
            p.relative_to(w.resolve())
            ok = True
            break
        except ValueError:
            continue
    if not ok:
        raise ToolError(f"exclusao fora das raizes de escrita: {p}")
    if not p.exists():
        raise ToolError(f"nao existe: {p}")
    if p.is_dir():
        raise ToolError("recusa excluir diretório (apenas arquivos)")
    p.unlink()
    return json.dumps({"deleted": str(p)}, ensure_ascii=False)


def tool_copy_file(args):
    src = args.get("src")
    dst = args.get("dst")
    if not src or not dst:
        raise ToolError("src e dst obrigatórios")
    sp = safe_read_path(src)
    if Path(dst).is_absolute():
        dp = Path(dst).resolve()
    else:
        dp = (PROJECT_DIR / dst).resolve()
    ok = False
    for w in WRITE_ROOTS:
        try:
            dp.relative_to(w.resolve())
            ok = True
            break
        except ValueError:
            continue
    if not ok:
        raise ToolError(f"destino fora das raizes de escrita: {dp}")
    dp.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(sp, dp)
    return json.dumps({"copied": str(sp), "to": str(dp)}, ensure_ascii=False)


def tool_move_file(args):
    src = args.get("src")
    dst = args.get("dst")
    if not src or not dst:
        raise ToolError("src e dst obrigatórios")
    sp = safe_read_path(src)
    if Path(dst).is_absolute():
        dp = Path(dst).resolve()
    else:
        dp = (PROJECT_DIR / dst).resolve()
    ok = False
    for w in WRITE_ROOTS:
        try:
            dp.relative_to(w.resolve())
            ok = True
            break
        except ValueError:
            continue
    if not ok:
        raise ToolError(f"movimentacao fora das raizes de escrita: {dp}")
    dp.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.move(str(sp), str(dp))
    return json.dumps({"moved": str(sp), "to": str(dp)}, ensure_ascii=False)


def tool_audit_run(args):
    """Auditor estatico (nota 0-10). Nao compila, nao negoccia, so le."""
    project = str(args.get("project", "")).strip()
    if not project:
        project = str(MQL5_DIR / "Experts" / "XAU_AI_PRO")
    path = safe_read_path(project)
    if not path.is_dir():
        raise ToolError(f"nao e uma pasta: {path}")
    if not AUDIT_PY.exists():
        raise ToolError(f"auditor ausente: {AUDIT_PY}")
    return run_cmd(
        [str(PY_EXE), "-W", "error::SyntaxWarning", str(AUDIT_PY), str(path)],
        cwd=TOOLS_DIR,
        timeout=180,
    )


def tool_scaffold_new(args):
    """Gera projecto modular. Escreve so dentro de XAU_AI_PRO (Scaffolds/)."""
    name = str(args.get("name", "")).strip()
    if not re.match(r"^[A-Z][A-Za-z0-9_]{1,31}$", name):
        raise ToolError("nome invalido: Maiuscula inicial, A-Z a-z 0-9 _ (2..32 caracteres)")
    if not SCAFFOLD_PY.exists():
        raise ToolError(f"gerador ausente: {SCAFFOLD_PY}")

    root_rel = str(args.get("root", "")).strip() or "Scaffolds"
    root = safe_write_path(root_rel)
    if root.suffix:
        raise ToolError("root tem de ser uma pasta, nao um ficheiro")

    cmd = [str(PY_EXE), str(SCAFFOLD_PY), "--name", name, "--root", str(root)]
    if bool(args.get("force", False)):
        cmd.append("--force")
    return run_cmd(cmd, cwd=TOOLS_DIR, timeout=120)


TOOLS = [
    {
        "name": "roots_info",
        "description": "Raizes fixas deste servidor e existencia do dataset/interpretador.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_roots_info,
    },
    {
        "name": "pipeline_run",
        "description": "Corre xau_model_tools.py com um comando permitido (validate/publish/regen/probe/stamp/train).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": list(ALLOWED_COMMANDS), "description": "Comando do pipeline."},
                "timeout_sec": {"type": "integer", "minimum": 30, "maximum": 7200},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
        "handler": tool_pipeline_run,
    },
    {
        "name": "audit_run",
        "description": "Auditor estatico de projeto MQL5: nota 0-10, erros/avisos, .ex5 vs .mq5, JSON. So le.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "pasta do projeto; omissao = Experts\\XAU_AI_PRO"}
            },
            "additionalProperties": False,
        },
        "handler": tool_audit_run,
    },
    {
        "name": "scaffold_new",
        "description": "Gera projeto MQL5 modular compilavel (9 ficheiros, execucao desligada) em XAU_AI_PRO\\Scaffolds\\<NAME>.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "nome do projeto (Maiuscula inicial)"},
                "root": {"type": "string", "description": "subpasta de XAU_AI_PRO; omissao = Scaffolds"},
                "force": {"type": "boolean"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "handler": tool_scaffold_new,
    },
    {
        "name": "dataset_info",
        "description": "Mede o dataset: linhas, simbolos, primeiro/ultimo bar, linhas malformadas.",
        "inputSchema": {
            "type": "object",
            "properties": {"file": {"type": "string", "description": "CSV em Files\\Data"}},
            "additionalProperties": False,
        },
        "handler": tool_dataset_info,
    },
    {
        "name": "prediction_get",
        "description": "Le Data\\prediction_<SIMBOLO>.json e devolve sinal/confianca/modelo.",
        "inputSchema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}, "timeframe": {"type": "string"}},
            "required": ["symbol"],
            "additionalProperties": False,
        },
        "handler": tool_prediction_get,
    },
    {
        "name": "validate_report",
        "description": "Le o relatorio de validacao dos JSON (json_validation_report.json).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_validate_report,
    },
    {
        "name": "git_status",
        "description": "git status curto do repositorio do projeto. So le.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_git_status,
    },
    {
        "name": "git_diff",
        "description": "git diff (opcionalmente --staged e limitado a um path). So le.",
        "inputSchema": {
            "type": "object",
            "properties": {"staged": {"type": "boolean"}, "path": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": tool_git_diff,
    },
    {
        "name": "git_log",
        "description": "Ultimos N commits em formato curto. So le.",
        "inputSchema": {
            "type": "object",
            "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 100}},
            "additionalProperties": False,
        },
        "handler": tool_git_log,
    },
    {
        "name": "run_tests",
        "description": "Corre pytest num path do projeto (marker e extra opcionais).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "marker": {"type": "string"},
                "extra": {"type": "string"},
                "timeout_sec": {"type": "integer", "minimum": 30, "maximum": 3600},
            },
            "additionalProperties": False,
        },
        "handler": tool_run_tests,
    },
    {
        "name": "run_lint",
        "description": "Corre flake8 num path (omissao: Python).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": tool_run_lint,
    },
    {
        "name": "file_read",
        "description": "Le um ficheiro (inteiro ou intervalo de linhas) dentro das raizes de leitura.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_file_read,
    },
    {
        "name": "file_write",
        "description": "Escreve um ficheiro dentro das raizes de escrita do projeto.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        "handler": tool_file_write,
    },
    {
        "name": "list_dir",
        "description": "Lista diretorio dentro de MQL5 (depth 1-6).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "depth": {"type": "integer", "minimum": 1, "maximum": 6}},
            "additionalProperties": False,
        },
        "handler": tool_list_dir,
    },
    {
        "name": "search_text",
        "description": "Busca textual no projeto (opcional path/glob).",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "path": {"type": "string"}, "glob": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "handler": tool_search_text,
    },
    {
        "name": "project_info",
        "description": "Informacoes do projeto (paths, git, python, tests).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_project_info,
    },
    {
        "name": "list_roots",
        "description": "Lista raizes de leitura (MQL5 + extras) e de escrita.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": tool_list_roots,
    },
    {
        "name": "add_read_root",
        "description": "Adiciona uma pasta externa as raizes de leitura (persiste em roots.json).",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_add_read_root,
    },
    {
        "name": "remove_read_root",
        "description": "Remove uma pasta externa das raizes de leitura.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_remove_read_root,
    },
    {
        "name": "run_command",
        "description": "Executa um comando permitido (python/git/node/npm/pip/metaeditor/flake8/pytest) sem shell.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "executable": {"type": "string", "enum": list(ALLOWED_EXECUTABLES.keys())},
                "args": {"oneOf": [{"type": "array", "items": {"type": "string"}}, {"type": "string"}]},
                "cwd": {"type": "string"},
                "timeout_sec": {"type": "integer", "minimum": 30, "maximum": 3600},
            },
            "required": ["executable"],
            "additionalProperties": False,
        },
        "handler": tool_run_command,
    },
    {
        "name": "npm_run",
        "description": "Corre 'npm run <script>' numa pasta (default frontend).",
        "inputSchema": {
            "type": "object",
            "properties": {"script": {"type": "string"}, "cwd": {"type": "string"}, "timeout_sec": {"type": "integer"}},
            "additionalProperties": False,
        },
        "handler": tool_npm_run,
    },
    {
        "name": "metaeditor_compile",
        "description": "Compila um arquivo MQL5 via MetaEditor CLI.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "defines": {"type": "string"},
                "include": {"type": "string"},
                "timeout_sec": {"type": "integer"},
            },
            "required": ["file"],
            "additionalProperties": False,
        },
        "handler": tool_metaeditor_compile,
    },
    {
        "name": "create_folder",
        "description": "Cria pasta dentro das raizes de escrita.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_create_folder,
    },
    {
        "name": "delete_file",
        "description": "Exclui arquivo (nao diretorio) dentro das raizes de escrita.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": tool_delete_file,
    },
    {
        "name": "copy_file",
        "description": "Copia arquivo (src pode ser qualquer root de leitura; dst dentro de escrita).",
        "inputSchema": {
            "type": "object",
            "properties": {"src": {"type": "string"}, "dst": {"type": "string"}},
            "required": ["src", "dst"],
            "additionalProperties": False,
        },
        "handler": tool_copy_file,
    },
    {
        "name": "move_file",
        "description": "Move arquivo entre raizes permitidas.",
        "inputSchema": {
            "type": "object",
            "properties": {"src": {"type": "string"}, "dst": {"type": "string"}},
            "required": ["src", "dst"],
            "additionalProperties": False,
        },
        "handler": tool_move_file,
    },
]

TOOL_MAP = {t["name"]: t for t in TOOLS}


# ----------------------------------------------------------------------
# JSON-RPC sobre stdio
# ----------------------------------------------------------------------
def rpc_result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def rpc_error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(req):
    method = req.get("method")
    msg_id = req.get("id")

    if method == "initialize":
        return rpc_result(
            msg_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return rpc_result(msg_id, {})
    if method == "tools/list":
        return rpc_result(
            msg_id,
            {
                "tools": [
                    {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
                    for t in TOOLS
                ]
            },
        )
    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        tool = TOOL_MAP.get(name)
        if tool is None:
            return rpc_error(msg_id, -32602, f"ferramenta desconhecida: {name}")
        try:
            text = tool["handler"](args)
            return rpc_result(
                msg_id,
                {"content": [{"type": "text", "text": clip(text)}], "isError": False},
            )
        except ToolError as exc:
            return rpc_result(
                msg_id,
                {"content": [{"type": "text", "text": f"RECUSA: {exc}"}], "isError": True},
            )
        except Exception as exc:  # noqa: BLE001
            return rpc_result(
                msg_id,
                {"content": [{"type": "text", "text": f"ERRO: {type(exc).__name__}: {exc}"}], "isError": True},
            )
    return rpc_error(msg_id, -32601, f"metodo desconhecido: {method}")


def serve():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stdout.write(json.dumps(rpc_error(None, -32700, f"parse error: {exc}")) + "\n")
            sys.stdout.flush()
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def selftest():
    checks = []

    def check(name, fn):
        try:
            out = fn()
            checks.append((name, "OK", str(out)[:240].replace("\n", " ")))
        except Exception as exc:  # noqa: BLE001
            checks.append((name, "FALHA", f"{type(exc).__name__}: {exc}"))

    check("initialize", lambda: handle({"id": 1, "method": "initialize"})["result"]["serverInfo"])
    check("tools/list", lambda: [t["name"] for t in handle({"id": 2, "method": "tools/list"})["result"]["tools"]])
    check("roots_info", lambda: json.loads(tool_roots_info({}))["read_roots"])
    check(
        "comando_recusado",
        lambda: handle(
            {"id": 3, "method": "tools/call", "params": {"name": "pipeline_run", "arguments": {"command": "rm -rf"}}}
        )["result"]["content"][0]["text"],
    )
    check("dataset_info", lambda: json.loads(tool_dataset_info({}))["linhas"])
    check("prediction_get", lambda: json.loads(tool_prediction_get({"symbol": "XAUUSD"}))["signal"])
    check("simbolo_vazio", lambda: handle(
        {"id": 4, "method": "tools/call", "params": {"name": "prediction_get", "arguments": {"symbol": ""}}}
    )["result"]["content"][0]["text"])
    check("validate_report", lambda: json.loads(tool_validate_report({}))["warnings_count"])
    check("audit_run", lambda: [ln for ln in tool_audit_run({}).splitlines() if ln.startswith("NOTA=")])
    check(
        "scaffold_nome_recusado",
        lambda: handle(
            {"id": 5, "method": "tools/call",
             "params": {"name": "scaffold_new", "arguments": {"name": "minusculo-invalido"}}}
        )["result"]["content"][0]["text"],
    )
    check("ferramentas_novas_no_registo", lambda: [n for n in ("audit_run", "scaffold_new") if n in TOOL_MAP])

    for name, state, detail in checks:
        print(f"[selftest] {state:5s} {name}: {detail}")
    falhas = sum(1 for _, s, _ in checks if s != "OK")
    print(f"[selftest] total={len(checks)} falhas={falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    serve()
