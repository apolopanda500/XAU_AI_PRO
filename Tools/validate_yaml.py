"""Validador de YAML para a auditoria do XAU_AI_PRO."""
import sys
from pathlib import Path
import yaml

ARQUIVOS = [
    r".gitlab-ci.yml",
    r".github\workflows\build.yml",
    r".github\workflows\deploy.yml",
    r".github\workflows\build-installer.yml",
    r".github\workflows\releases.yml",
    r"docker-compose.yml",
    r"litellm\docker-compose.yml",
    r"litellm\litellm_config.yaml",
]

BASE = Path(__file__).resolve().parents[1]

falhas = 0
for rel in ARQUIVOS:
    caminho = BASE / rel
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            list(yaml.safe_load_all(f))
        print(f"OK      {rel}")
    except FileNotFoundError:
        print(f"SKIP    {rel} (nao encontrado)")
    except Exception as e:
        falhas += 1
        print(f"ERRO    {rel}: {e}")

sys.exit(1 if falhas else 0)
