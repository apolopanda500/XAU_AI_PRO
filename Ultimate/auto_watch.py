"""
XAU AI PRO — Auto Watch (auto-approve contínuo)
Executa o fluxo treinar -> predizer -> validar em loop, gravando relatórios
de aprovação em Reports/ e atualizando as predições consumidas pelo EA.

Configuração (variáveis de ambiente / edição):
    WATCH_INTERVAL   segundos entre execuções (padrão 3600)
    WATCH_DRY_STATS  "1" para apenas reportar stats sem treinar (padrão relatório completo)

Uso:
    python auto_watch.py
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

try:
    import auto_engine as ae
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import auto_engine as ae

try:
    import config_store as cs
except ModuleNotFoundError:
    import sys as _s

    _s.path.insert(0, str(Path(__file__).resolve().parent))
    import config_store as cs

# Intervalo em SEGUNDOS: prioridade 1) --interval/min 2) WATCH_INTERVAL env
# (em segundos) 3) config da GUI (em minutos) 4) padrão 3600
import argparse

_parser = argparse.ArgumentParser(description="auto_watch do XAU AI PRO")
_parser.add_argument("--interval", type=int, default=None,
                     help="intervalo em minutos")
_parser.add_argument("--once", action="store_true",
                     help="executa apenas uma vez e sai (útil p/ agendador)")
_args, _ = _parser.parse_known_args()


def _get_interval_seconds() -> int:
    cfg_interval = None
    try:
        cfg_interval = cs.get_api_config().get("refresh_seconds")
    except Exception:
        cfg_interval = None
    if _args.interval is not None:
        return int(_args.interval) * 60  # minutos -> segundos
    env_val = os.getenv("WATCH_INTERVAL")
    if env_val:
        return int(env_val)
    if cfg_interval:
        return int(cfg_interval) * 60
    return 3600


def _banner(rep: dict) -> None:
    verdict = rep.get("verdict", {})
    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AUTO-WATCH")
    print("=" * 60)
    print(f"  Dataset   : {rep['dataset'].get('rows', '-')} amostras | "
          f"símbolos: {rep['dataset'].get('symbols', [])} | "
          f"período: {rep['dataset'].get('period')}")
    print(f"  Treino    : {'OK' if rep['training'].get('ok') else 'FALHOU'}")
    print(f"  Predições : {len(rep.get('predictions', []))} arquivos")
    approved = verdict.get("approved")
    print(f"  Aprovado  : {approved}")
    if approved is None:
        print("  (modo relatório — sem decisão de aprovação)")
    else:
        for ch in verdict.get("checks", []):
            print(f"    [{'v' if ch['ok'] else 'x'}] {ch['name']}: {ch['detail']}")
    print(f"  Relatório : {rep.get('report_file')}")
    if not approved:
        print("  >>> CONDIÇÕES NÃO APROVADAS. Acumule dados antes de operar com IA.")
    print("=" * 60 + "\n")


def main() -> None:
    dry = os.getenv("WATCH_DRY_STATS", "") == "1"
    interval = _get_interval_seconds()
    print(f"AUTO-WATCH iniciado. Intervalo: {interval}s | dry_stats={dry}")
    while True:
        started = time.time()
        try:
            if dry:
                rep = {
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "dataset": ae.dataset_stats(),
                    "training": {"ok": None},
                    "predictions": ae.list_predictions(),
                    "verdict": {"approved": None, "checks": []},
                    "report_file": None,
                }
            else:
                rep = ae.run_full()
            _banner(rep)
        except Exception as e:
            print(f"[ERRO] {e}")
        elapsed = time.time() - started
        if _args.once:
            print("Auto-watch concluiu a execução única. Encerrando.")
            break
        time.sleep(max(10, interval - elapsed))


if __name__ == "__main__":
    main()