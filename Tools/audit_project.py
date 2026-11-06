#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""audit_project.py -- auditor estatico de um projecto MQL5. Nota 0..10.

Nao substitui o compilador: mede o que o compilador NAO ve --
encoding, includes, binario velho, risco sem trava, log sem gate,
ordens sem verificacao de retcode, JSON invalido.

Uso:
  python.exe audit_project.py "<pasta do projecto>"
  python.exe audit_project.py "<pasta do projecto>" --json "C:\...\audit.json"
  python.exe audit_project.py --selftest

Codigo de saida: 0 = sem ERROS, 1 = pelo menos um ERRO.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve()
MQL5_DIR = HERE.parents[3]          # ...\MQL5
DATA_DIR = MQL5_DIR / "Files" / "Data"

SOURCE_EXT = {".mq5", ".mqh"}
INCLUDE_RE = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]', re.MULTILINE)
RISK_KEYS = ("RiskPercent", "MaxDailyLoss", "MaxDrawdown")
TRADE_CALLS = ("OrderSend(", ".Buy(", ".Sell(", "PositionClose(", "PositionModify(")

WEIGHT_ERROR = 1.0
WEIGHT_WARN = 0.3


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, msg: str, path: str = "") -> None:
        self.items.append({"level": level, "code": code, "message": msg, "path": path})

    def error(self, code: str, msg: str, path: str = "") -> None:
        self.add("ERRO", code, msg, path)

    def warn(self, code: str, msg: str, path: str = "") -> None:
        self.add("AVISO", code, msg, path)

    def info(self, code: str, msg: str, path: str = "") -> None:
        self.add("INFO", code, msg, path)

    def count(self, level: str) -> int:
        return sum(1 for i in self.items if i["level"] == level)

    def score(self) -> float:
        # Cada CODIGO desconta no maximo 3 vezes. Um achado cosmetico
        # repetido 28 vezes nao pode valer mais do que 28 defeitos reais.
        pesos = {"ERRO": WEIGHT_ERROR, "AVISO": WEIGHT_WARN}
        usados: dict[str, int] = {}
        penalidade = 0.0
        for item in self.items:
            w = pesos.get(item["level"], 0.0)
            if w == 0.0:
                continue
            n = usados.get(item["code"], 0)
            if n >= 3:
                continue
            usados[item["code"]] = n + 1
            penalidade += w
        return max(0.0, min(10.0, 10.0 - penalidade))


def strip_noise(text: str) -> str:
    """Remove comentarios e literais de string para contar { } a serio."""
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        elif c == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
        elif c == "'":
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == "'":
                    i += 1
                    break
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def brace_delta(text: str) -> int:
    clean = strip_noise(text)
    return clean.count("{") - clean.count("}")


def resolve_include(name: str, from_file: Path, quoted: bool) -> Path | None:
    name = name.replace("/", "\\")
    if quoted:
        cand = from_file.parent / name
        if cand.is_file():
            return cand
    cand = MQL5_DIR / "Include" / name
    if cand.is_file():
        return cand
    cand = MQL5_DIR / name
    if cand.is_file():
        return cand
    return None


def audit_sources(project: Path, rep: Report) -> list[Path]:
    files = sorted([p for p in project.rglob("*") if p.suffix.lower() in SOURCE_EXT])
    if not files:
        rep.error("A001", "nenhum .mq5/.mqh encontrado em " + str(project))
        return []

    bom: list[str] = []

    for f in files:
        rel = str(f.relative_to(project))
        raw = f.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            rep.error("A002", "nao e UTF-8 valido", rel)
            continue

        if raw.startswith(b"\xef\xbb\xbf"):
            bom.append(rel)

        d = brace_delta(text)
        if d != 0:
            rep.error("A004", "chaves desbalanceadas (delta=" + str(d) + ")", rel)

        if "\t" in text:
            rep.warn("A005", "contem TAB (o projecto usa 3 espacos)", rel)

        for m in INCLUDE_RE.finditer(text):
            inc = m.group(1)
            quoted = '"' in m.group(0)
            if resolve_include(inc, f, quoted) is None:
                rep.error("A006", "#include nao resolve: " + inc, rel)

    if bom:
        amostra = ", ".join(bom[:3]) + (" ..." if len(bom) > 3 else "")
        rep.info("A003", str(len(bom)) + " ficheiro(s) com BOM UTF-8 (o compilador aceita; "
                          "e inconsistencia de encoding, nao defeito): " + amostra)
    return files


def audit_trading(project: Path, files: list[Path], rep: Report) -> None:
    corpus = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files)

    if not any(k in corpus for k in RISK_KEYS):
        rep.error("B001", "nenhum parametro de risco encontrado (RiskPercent/MaxDailyLoss/MaxDrawdown)")

    magic = ("SetExpertMagicNumber" in corpus or "InpMagic" in corpus
             or "MagicNumber" in corpus or "magic" in corpus.lower())
    if not magic:
        rep.error("B002", "magic number ausente: impossivel separar posicoes do EA")

    trading = any(t in corpus for t in TRADE_CALLS)
    if trading:
        if "retcode" not in corpus and "ResultRetcode" not in corpus:
            rep.error("B003", "ha chamadas de negociacao sem verificacao de retcode")
        if "MQL_TRADE_ALLOWED" not in corpus and "TERMINAL_TRADE_ALLOWED" not in corpus:
            rep.warn("B004", "EA negoceia sem verificar permissao de negociacao (MQL_TRADE_ALLOWED)")
        if "PositionSelect" in corpus and "POSITION_MAGIC" not in corpus:
            rep.warn("B005", "PositionSelect sem filtro POSITION_MAGIC: risco de gerir posicao alheia")
    else:
        rep.info("B000", "nenhuma chamada de negociacao (esqueleto ou EA de leitura)")

    todo = len(re.findall(r"\b(TODO|FIXME|XXX)\b", corpus))
    if todo:
        rep.info("B006", str(todo) + " marcador(es) TODO/FIXME no codigo")

    if "DiagGateAllow" in corpus:
        gates = corpus.count("DiagGateAllow")
        rep.info("B007", "DiagGateAllow usado " + str(gates) + "x (log com anti-repeticao)")
    else:
        prints = corpus.count("Print(")
        if prints > 10:
            rep.warn("B008", str(prints) + " Print() sem DiagGate: journal vai repetir")

    if "iATR(" in corpus and "IndicatorRelease" not in corpus:
        rep.warn("B009", "handle de indicador criado sem IndicatorRelease no OnDeinit")

    if "OnTick" in corpus and "iTime(" not in corpus and "Bars(" not in corpus:
        rep.warn("B010", "OnTick sem guarda de barra nova: decide a cada tick")


def audit_binary(project: Path, rep: Report) -> None:
    ex5s = sorted(project.rglob("*.ex5"))
    if not ex5s:
        rep.warn("C001", "nenhum .ex5: nada compilado ainda (ou pasta de fontes)")
        return
    for ex5 in ex5s:
        src = ex5.with_suffix(".mq5")
        if not src.is_file():
            rep.info("C002", ".ex5 sem .mq5 ao lado: " + ex5.name)
            continue
        if ex5.stat().st_mtime < src.stat().st_mtime:
            rep.error("C003", "binario MAIS VELHO que o fonte (o terminal corre codigo antigo): "
                              + ex5.name)
        else:
            rep.info("C004", ex5.name + " mais recente que o fonte (ok)")


def audit_json(rep: Report) -> None:
    if not DATA_DIR.is_dir():
        rep.info("D000", "sem pasta Files\\Data para validar")
        return
    total = ok = 0
    for jf in sorted(DATA_DIR.glob("*.json")):
        total += 1
        try:
            json.loads(jf.read_text(encoding="utf-8", errors="replace"))
            ok += 1
        except Exception as exc:                     # noqa: BLE001
            rep.error("D001", "JSON invalido: " + jf.name + " -> " + str(exc)[:120])
    if total:
        rep.info("D002", "JSON em Files\\Data: " + str(total) + " ficheiros, " + str(ok) + " validos")


def run(project: Path) -> Report:
    rep = Report()
    if not project.is_dir():
        rep.error("A000", "pasta inexistente: " + str(project))
        return rep
    files = audit_sources(project, rep)
    if files:
        audit_trading(project, files, rep)
    audit_binary(project, rep)
    audit_json(rep)
    return rep


def selftest() -> int:
    import tempfile

    fails = total = 0

    def check(label: str, ok: bool) -> None:
        nonlocal fails, total
        total += 1
        print(("  OK   " if ok else "  FALHA") + " | " + label)
        if not ok:
            fails += 1

    check("chaves equilibradas", brace_delta("void f(){ if(1){ } }") == 0)
    check("chave a mais detectada", brace_delta("void f(){ } }") == -1)
    check("chave em falta detectada", brace_delta("void f(){ if(1){ }") == 1)
    check("chave dentro de string ignorada", brace_delta('string s="{";') == 0)
    check("chave dentro de comentario ignorada", brace_delta("// {\nint a;") == 0)
    check("chave dentro de bloco /* */ ignorada", brace_delta("/* { */ int a;") == 0)

    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "P"
        proj.mkdir()
        (proj / "P.mq5").write_text(
            "#include \"Core\\Config.mqh\"\n"
            "input double InpRiskPercent=0.5;\n"
            "input long InpMagic=1;\n"
            "void OnTick(){ if(iTime(_Symbol,PERIOD_CURRENT,0)>0){} }\n",
            encoding="utf-8",
        )
        rep = run(proj)
        check("include em falta vira ERRO", rep.count("ERRO") >= 1)
        check("nota nunca sai de 0..10", 0.0 <= rep.score() <= 10.0)

    ruido = Report()
    for _ in range(10):
        ruido.warn("A003", "mesmo achado cosmetico")
    check("codigo repetido desconta no maximo 3x", abs(ruido.score() - 9.1) < 1e-9)

    misto = Report()
    for i in range(3):
        misto.error("E" + str(i), "defeito distinto")
    check("3 defeitos distintos valem 3x", abs(misto.score() - 7.0) < 1e-9)

    return 0 if fails == 0 else 1


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Auditor estatico de projecto MQL5 (nota 0..10).")
    ap.add_argument("project", nargs="?", help="pasta do projecto (Experts\\NOME)")
    ap.add_argument("--json", dest="json_out", default="", help="gravar o relatorio em JSON")
    ap.add_argument("--selftest", action="store_true", help="correr as provas internas")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.project:
        ap.print_help()
        return 2

    project = Path(args.project).resolve()
    rep = run(project)

    print("=" * 66)
    print("AUDITORIA: " + str(project))
    print("quando   : " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 66)
    for item in rep.items:
        loc = (" | " + item["path"]) if item["path"] else ""
        print("[" + item["level"] + "] " + item["code"] + " | " + item["message"] + loc)

    erros, avisos = rep.count("ERRO"), rep.count("AVISO")
    nota = rep.score()
    print("-" * 66)
    print("ERROS=" + str(erros) + " AVISOS=" + str(avisos) + " INFO=" + str(rep.count("INFO")))
    print("NOTA=" + ("%.1f" % nota) + "/10")
    print("-" * 66)

    if args.json_out:
        payload = {
            "project": str(project),
            "when": datetime.now().isoformat(timespec="seconds"),
            "errors": erros,
            "warnings": avisos,
            "score": round(nota, 1),
            "items": rep.items,
        }
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print("relatorio: " + str(out))

    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
