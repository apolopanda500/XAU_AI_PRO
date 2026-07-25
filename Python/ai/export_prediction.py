from pathlib import Path
import shutil
import json

ROOT = Path(__file__).resolve().parents[2]

# =====================================
# ORIGEM PYTHON
# =====================================

SOURCE = Path(__file__).resolve().parent / "prediction.json"

# =====================================
# DESTINO MT5
# Ajuste se necessário
# =====================================

DEST = ROOT / "MQL5" / "Files" / "AI" / "prediction.json"



# =====================================
# CRIAR PASTA
# =====================================

DEST.parent.mkdir(
    parents=True,
    exist_ok=True
)



# =====================================
# COPIAR ARQUIVO
# =====================================

if not SOURCE.exists():

    raise FileNotFoundError(
        "prediction.json não encontrado"
    )


shutil.copy(
    SOURCE,
    DEST
)



print("==============================")
print("AI BRIDGE EXPORT")
print("==============================")

print("Origem:")
print(SOURCE)

print()

print("Destino:")
print(DEST)

print()

print("Prediction enviado para MT5")