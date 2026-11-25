"""Os assets do frontend precisam chegar ao APK.

POR QUE ESTE TESTE EXISTE (25/11/2026)
=====================================
MEDIDO no APK assinado 1.2.191: o `libxau_ai_pro_desktop_lib.so` continha
`/index.html`, `/favicon.ico` e `/assets/*.js|css`, mas NAO continha
`/xau-ai-pro-mark.png` nem `/xau-ai-pro-quantum-cover.png`. No PC os PNGs
estavam em `frontend/public/` e o desktop parecia certo; no checkout limpo do
CI eles nao existiam porque estavam no `.gitignore`. Resultado: logo, capa e
favicon quebrados no APK — exatamente o sintoma "selos e imagens bugado".

O teste exercita o caminho que importa: o arquivo existe em disco, o git NAO
o ignora e ele esta versionado. Um arquivo que existe so na maquina do operador
nao e asset — e localmente e impossivel perceber a diferenca sem esta trava.
"""

from pathlib import Path
import subprocess

RAIZ = Path(__file__).resolve().parent.parent

ASSETS = (
    "frontend/public/xau-ai-pro-mark.png",
    "frontend/public/xau-ai-pro-quantum-cover.png",
    "frontend/public/favicon.png",
)


def _git(*argumentos: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argumentos],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )


def test_assets_do_frontend_existem_e_nao_sao_ignorados() -> None:
    for relativo in ASSETS:
        caminho = RAIZ / relativo
        assert caminho.is_file(), f"asset do frontend ausente: {relativo}"
        assert caminho.stat().st_size > 0, f"asset zerado: {relativo}"

        ignorado = _git("check-ignore", "-q", "--", relativo)
        assert ignorado.returncode == 1, (
            f"{relativo} esta ignorado pelo git; o checkout do CI nao tera o arquivo"
        )

        versionado = _git("ls-files", "--error-unmatch", "--", relativo)
        assert versionado.returncode == 0, f"{relativo} nao esta versionado"


def test_prova_negativa_as_regras_de_ignore_continuam_ativas() -> None:
    """Se tudo passasse a ser versionado, a trava acima nao provaria nada."""
    ignorado = _git("check-ignore", "-q", "--", "Docs/branding/asset-local.png")
    assert ignorado.returncode == 0, "a regra Docs/branding/*.png deixou de ignorar"
