# Mede a validade REAL de todos os modelos treinados (25/10/2026, pedido do
# dono: "os modelos validar real todos"). Um modelo e "real" quando:
#   1. o artefato .pkl EXISTE no disco;
#   2. CARREGA pelo consumidor real — `joblib.load`, o mesmo do gateway
#      (`ai_inference.py`); o treino grava com `joblib.dump`. Pickle puro
#      reprova por motivo errado ("STACK_GLOBAL requires str") e e a
#      armadilha do AGENTS.md 5: medir com a ferramenta do produtor.
#   3. EXECUTA inferencia: predict_proba/predict numa linha de zeros no
#      `n_features_in_` que o proprio modelo declara. Dado SINTETICO,
#      rotulado como tal (AGENTS.md 12): a validacao aqui e estrutural
#      (o modelo executa com o contrato de features), nao de mercado.
# So contar arquivo e contar metade: um .pkl corrompido tem tamanho de .pkl.
import json
import pathlib

import joblib
import numpy as np

d = pathlib.Path("Python/models")
metas = sorted(d.glob("*.meta.json"))
print(f"metas={len(metas)}")
linhas = []
erros = []
for meta_path in metas:
    nome = meta_path.name.replace(".meta.json", "")
    pkl_path = d / f"{nome}.pkl"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    metrics = meta.get("metrics", {})
    existe = pkl_path.exists()
    carrega = False
    executa = False
    if existe:
        try:
            modelo = joblib.load(pkl_path)
            carrega = hasattr(modelo, "predict_proba") or hasattr(modelo, "predict")
            n = getattr(modelo, "n_features_in_", None)
            if n is None and hasattr(modelo, "estimators_"):
                n = getattr(modelo.estimators_[0], "n_features_in_", None)
            if n:
                zero = np.zeros((1, int(n)), dtype=float)
                try:
                    if hasattr(modelo, "predict_proba"):
                        modelo.predict_proba(zero)
                    else:
                        modelo.predict(zero)
                    executa = True
                except Exception as exc:  # noqa: BLE001
                    erros.append(f"{nome}: inferencia falhou: {exc}")
        except Exception as exc:  # noqa: BLE001 - contabilidade, nao controle
            carrega = False
            erros.append(f"{nome}: carregamento falhou: {exc}")
    contrato = bool(
        meta.get("feature_version") and meta.get("timeframe") and meta.get("symbol")
    )
    linhas.append(
        (
            nome,
            existe,
            carrega,
            executa,
            contrato,
            bool(meta.get("publicable")),
            metrics.get("edge"),
            metrics.get("accuracy"),
            meta.get("train_date", ""),
        )
    )

total = len(linhas)
existe_n = sum(1 for r in linhas if r[1])
carrega_ok = sum(1 for r in linhas if r[2])
executa_ok = sum(1 for r in linhas if r[3])
contrato_ok = sum(1 for r in linhas if r[4])
pub = sum(1 for r in linhas if r[5])
print(
    f"artefato existe: {existe_n}/{total}  carrega: {carrega_ok}/{total}  "
    f"executa inferencia: {executa_ok}/{total}  "
    f"contrato: {contrato_ok}/{total}  publicavel: {pub}/{total}"
)
for n, p, c, ex, ct, pu, e, a, td in linhas:
    marc = "ok " if p and c and ex and ct else ("MEIO" if p and c else "FALTA")
    edge_s = f"{e:+.4f}" if isinstance(e, (int, float)) else "None"
    acc_s = f"{a:.4f}" if isinstance(a, (int, float)) else "None"
    print(
        f"{marc} pub={int(pu)} exec={int(ex)} edge={edge_s} "
        f"acc={acc_s} contrato={int(ct)} {n} @{td}"
    )
if erros:
    print("--- erros:")
    for e in erros:
        print(f"  {e}")
# A medicao e o veredito: sair 0 so se TUDO existir, carregar e executar.
raise SystemExit(0 if existe_n == total == carrega_ok == executa_ok else 1)
