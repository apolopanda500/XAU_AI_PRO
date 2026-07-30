"""Export helpers for XAU_AI_PRO."""

from pathlib import Path
import json


def save_prediction(result, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=4, ensure_ascii=False), encoding="utf-8")
    return path
