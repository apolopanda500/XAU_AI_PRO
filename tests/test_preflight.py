"""Testes do pre-flight de ambiente.

O pre-flight existe porque os erros caros deste projeto apareciam no meio de
operacoes longas: o build do Android consumiu 3,4 GB e so entao o emulador
avisou "not enough space"; um binario solto na raiz ficou travado por estar em
uso; um script falhava de forma opaca quando recebia array via `-File`.

Estes testes fixam o comportamento de cada verificacao isoladamente, inclusive
quando o comando externo falha ou o disco nao pode ser lido.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import preflight as pf

# O pre-flight valida o ambiente de OPERACAO, que e Windows: o app usa
# MetaTrader5, DPAPI e `.venv\Scripts\python.exe`. Este teste sobe o
# executavel do venv por caminho, entao em runner Linux ele falha com
# FileNotFoundError antes de testar o preflight.
#
# Nao e um defeito do preflight nem do codigo — e o teste rodando onde o
# produto nao roda. O CI Linux de `xau-ai-pro-validation.yml` executa a
# suite inteira; este teste e de plataforma e fica coberto pelo job
# `validate`, que roda em `windows-latest`.
_SO_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32",
    reason="pre-flight de operacao exige Windows: .venv\\Scripts\\python.exe, DPAPI e MetaTrader5",
)


class _RelatorioVazio(pf.Relatorio):
    pass


def _resultado(nome: str) -> pf.Resultado:
    return next(r for r in pf.checar_ferramentas() if r.nome.endswith(nome))


# ------------------------------------------------------------------- disco


def test_disco_ausente_e_falha_com_dica_de_limpeza():
    resultado = pf.checar_disco(minimo_gb=10_000.0)
    assert resultado.estado == pf.ESTADOS["falha"]
    # A dica precisa apontar a ferramenta de limpeza do proprio projeto.
    assert "limpeza_segura.ps1" in resultado.dica


def test_disco_justo_no_limite_passa():
    livre = pf.shutil.disk_usage(pf.ROOT).free / (1024 ** 3)
    assert pf.checar_disco(minimo_gb=livre * 0.5).estado == pf.ESTADOS["ok"]


def test_disco_entre_o_minimo_e_o_dobro_e_aviso():
    livre = pf.shutil.disk_usage(pf.ROOT).free / (1024 ** 3)
    resultado = pf.checar_disco(minimo_gb=livre * 0.75)
    assert resultado.estado == pf.ESTADOS["aviso"]
    assert "cuidado" in resultado.dica


def test_android_exige_mais_espaco_que_operacao_comum():
    assert pf.DISCO_MINIMO_ANDROID_GB > pf.DISCO_MINIMO_GB


# -------------------------------------------------------------- ferramentas


def test_ferramenta_ausente_nao_derruba_o_preflight(monkeypatch):
    monkeypatch.setattr(pf.shutil, "which", lambda nome: None)
    estados = [r.estado for r in pf.checar_ferramentas()]
    assert estados and all(e in pf.ESTADOS.values() for e in estados)


def test_ferramenta_que_quebra_nao_derruba_o_preflight(monkeypatch):
    def explode(*args, **kwargs):
        raise OSError("sem permissao")

    monkeypatch.setattr(pf.shutil, "which", lambda nome: "C:\\falso\\" + nome)
    monkeypatch.setattr(pf.subprocess, "run", explode)
    resultados = pf.checar_ferramentas()
    assert resultados
    assert all(r.estado in {pf.ESTADOS["aviso"], pf.ESTADOS["falha"]} for r in resultados)


def test_npm_chamado_com_extensao_no_windows():
    # No Windows `npm` e um .cmd: sem a extensao o subprocesso falha com WinError 2.
    if pf.os.name != "nt":
        pytest.skip("especifico do Windows")
    comando = dict(pf.FERRAMENTAS)["npm"][0]
    assert comando.endswith(".cmd")


# ------------------------------------------------------------------ python


def test_python_do_projeto_ausente_tem_instrucao():
    resultado = pf.checar_python_do_projeto()
    if resultado.estado == pf.ESTADOS["falha"]:
        assert "requirements" in resultado.dica


# ------------------------------------------------------------------ portas


def test_porta_livre_detecta_socket_ocupado():
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        porta = s.getsockname()[1]
        assert pf.porta_livre(porta) is False


def test_portas_ignoradas_quando_o_app_esta_rodando():
    # Com o app instalado e aberto, portas ocupadas sao esperadas.
    resultados = pf.checar_portas(esperar_livre=False)
    assert all(r.estado == pf.ESTADOS["ok"] for r in resultados)


def test_portas_ocupadas_bloqueiam_operacao_longa(monkeypatch):
    monkeypatch.setattr(pf, "porta_livre", lambda porta: False)
    resultados = pf.checar_portas(esperar_livre=True)
    assert all(r.estado == pf.ESTADOS["falha"] for r in resultados)
    assert all("feche o app" in r.dica for r in resultados)


# --------------------------------------------------------------------- mql5


def test_mql5_intacto_nao_falha():
    """MQL5 sem diff e `ok`.

    O `_git` e substituido em vez de ler o repositorio de verdade: este teste
    mede a GUARDA, e a guarda mede o que o `git status` devolve. Ler o
    working tree faz o teste depender de haver (ou nao) um `.mqh` modificado
    em mao — em 03/10/2026 ele reprovou porque o cooldown de margem estava
    sendo escrito, e a falha parecia ser do preflight quando era do contexto.
    """
    original = pf._git

    def falso(*args):
        if args[:2] == ("status", "--porcelain"):
            return 0, ""
        return original(*args)

    pf._git = falso
    try:
        resultado = pf.checar_mql5()
    finally:
        pf._git = original
    assert resultado.estado == pf.ESTADOS["ok"]


def test_mql5_modificado_sem_autorizacao_bloqueia():
    """Alteracao NAO declarada continua bloqueando — a guarda nao foi afrouxada.

    Este e o teste que impede que a `AUTORIZACOES_MQL5` vire um atalho para
    desligar a protecao: basta declarar uma vez e a guarda deixa de valer.
    """
    original = pf._git

    def falso(*args):
        if args[:2] == ("status", "--porcelain"):
            return 0, " M MQL5/Experts/XAU_AI_PRO/Core/AlgoQueNaoFoiAutorizado.mqh"
        return original(*args)

    pf._git = falso
    try:
        resultado = pf.checar_mql5()
    finally:
        pf._git = original
    assert resultado.estado == pf.ESTADOS["falha"], (
        "alteracao MQL5 sem autorizacao precisa reprovar; se este teste falha, "
        "a guarda foi afrouxada em vez de exigir declaracao"
    )
    assert "AUTORIZACOES_MQL5" in resultado.dica


def test_mql5_autorizado_e_aviso_nao_falha():
    """Alteracao DECLARADA passa como `aviso`, nunca como `ok`.

    `aviso` e o estado certo: o arquivo mudou e foi autorizado, mas o
    `preflight` nao pode afirmar que a alteracao esta valida — compilou e
    reanexou sao passos de fora do repositorio, e a propria guarda avisa isso.
    """
    original = pf._git
    autorizado = next(iter(pf.AUTORIZACOES_MQL5))

    def falso(*args):
        if args[:2] == ("status", "--porcelain"):
            return 0, f" M MQL5/Experts/XAU_AI_PRO/{autorizado}"
        return original(*args)

    pf._git = falso
    try:
        resultado = pf.checar_mql5()
    finally:
        pf._git = original
    assert resultado.estado == pf.ESTADOS["aviso"], (
        f"alteracao autorizada devia dar aviso, deu {resultado.estado}"
    )
    assert "REANEXOU" in resultado.dica or "REANEX" in resultado.dica


def test_mql5_modificado_bloqueia():
    original = pf._git

    def falso(*args):
        if args[:2] == ("status", "--porcelain"):
            return 0, " M MQL5/Experts/XAU_AI_PRO/XAU_AI_PRO.mq5"
        return original(*args)

    pf._git = falso
    try:
        resultado = pf.checar_mql5()
    finally:
        pf._git = original
    assert resultado.estado == pf.ESTADOS["falha"]
    assert "git checkout" in resultado.dica


# ------------------------------------------------------------------ limpeza


def test_scripts_bloqueados_ausentes():
    assert pf.checar_scripts_bloqueados().estado == pf.ESTADOS["ok"]


def test_script_bloqueado_presente_bloqueia(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "SCRIPTS_BLOQUEADOS", ("cmd.exe",))
    (tmp_path / "cmd.exe").write_bytes(b"MZ")
    monkeypatch.setattr(pf, "ROOT", tmp_path)
    resultado = pf.checar_scripts_bloqueados()
    assert resultado.estado == pf.ESTADOS["falha"]
    assert "cmd.exe" in resultado.detalhe


def test_binario_na_raiz_bloqueia(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "ROOT", tmp_path)
    (tmp_path / "app.exe").write_bytes(b"MZ")
    resultado = pf.checar_binarios_na_raiz()
    assert resultado.estado == pf.ESTADOS["falha"]
    assert "sombreia" in resultado.dica


def test_raiz_limpa_passa(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "ROOT", tmp_path)
    assert pf.checar_binarios_na_raiz().estado == pf.ESTADOS["ok"]
    assert pf.checar_scripts_bloqueados().estado == pf.ESTADOS["ok"]


# -------------------------------------------------------------------- flags


def test_flag_de_dinheiro_real_ligada_bloqueia(monkeypatch):
    monkeypatch.setenv("XAU_ENABLE_REAL_ORDERS", "1")
    resultado = pf.checar_flags_de_execucao()
    assert resultado.estado == pf.ESTADOS["falha"]
    assert "XAU_ENABLE_REAL_ORDERS" in resultado.detalhe


def test_flag_de_demo_nao_bloqueia(monkeypatch):
    for flag in pf.FLAGS_DE_EXECUCAO:
        monkeypatch.delenv(flag, raising=False)
    monkeypatch.setenv("XAU_ENABLE_TRADE_COMMANDS", "1")
    resultado = pf.checar_flags_de_execucao()
    assert resultado.estado == pf.ESTADOS["ok"]
    assert "paper/demo" in resultado.detalhe


# ------------------------------------------------------------------ relatorio


def test_relatorio_agrega_falhas_e_avisos():
    relatorio = _RelatorioVazio()
    relatorio.add(pf.Resultado("a", pf.ESTADOS["ok"]))
    relatorio.add(pf.Resultado("b", pf.ESTADOS["aviso"]))
    relatorio.add(pf.Resultado("c", pf.ESTADOS["falha"]))
    assert len(relatorio.falhas) == 1
    assert len(relatorio.avisos) == 1
    assert relatorio.ok_para_operacao_longa() is False


def test_relatorio_sem_falha_libera_operacao():
    relatorio = _RelatorioVazio()
    relatorio.add(pf.Resultado("a", pf.ESTADOS["ok"]))
    relatorio.add(pf.Resultado("b", pf.ESTADOS["aviso"]))
    assert relatorio.ok_para_operacao_longa() is True


def test_executar_nao_levanta():
    relatorio = pf.executar("longa")
    assert relatorio.resultados
    nomes = {r.nome for r in relatorio.resultados}
    assert "guarda MQL5" in nomes
    assert any("porta 9001" in n for n in nomes)


def test_imprimir_marca_cada_estado(capsys):
    relatorio = _RelatorioVazio()
    relatorio.add(pf.Resultado("a", pf.ESTADOS["ok"], "detalhe"))
    relatorio.add(pf.Resultado("b", pf.ESTADOS["aviso"], "aviso", "faça X"))
    relatorio.add(pf.Resultado("c", pf.ESTADOS["falha"], "erro", "faça Y"))
    pf.imprimir(relatorio)
    saida = capsys.readouterr().out
    assert "[ ok ]" in saida
    assert "[ !! ]" in saida
    assert "[XX  ]" in saida
    # As dicas precisam aparecer: e o que torna o relatorio util.
    assert "faça X" in saida and "faça Y" in saida
    assert "BLOQUEADO" in saida


def test_saida_json_e_analisavel(capsys, monkeypatch):
    import json

    relatorio = _RelatorioVazio()
    relatorio.add(pf.Resultado("x", pf.ESTADOS["ok"], "detalhe"))
    monkeypatch.setattr(pf, "executar", lambda etapa: relatorio)
    monkeypatch.setattr("sys.argv", ["preflight.py", "--json"])
    assert pf.main() == 0
    dados = json.loads(capsys.readouterr().out)
    assert dados["ok"] is True
    assert dados["itens"][0]["nome"] == "x"


def test_main_retorna_1_quando_ha_falha(monkeypatch):
    falho = _RelatorioVazio()
    falho.add(pf.Resultado("x", pf.ESTADOS["falha"]))
    monkeypatch.setattr(pf, "executar", lambda etapa: falho)
    monkeypatch.setattr("sys.argv", ["preflight.py", "--json"])
    assert pf.main() == 1


def test_main_retorna_0_sem_falha(monkeypatch):
    limpo = _RelatorioVazio()
    limpo.add(pf.Resultado("x", pf.ESTADOS["ok"]))
    monkeypatch.setattr(pf, "executar", lambda etapa: limpo)
    monkeypatch.setattr("sys.argv", ["preflight.py"])
    assert pf.main() == 0


def test_preflight_nao_altera_nada(tmp_path, monkeypatch):
    # Somente leitura: rodar o preflight nao pode criar arquivo na raiz.
    monkeypatch.setattr(pf, "ROOT", tmp_path)
    antes = sorted(p.name for p in tmp_path.iterdir())
    pf.checar_binarios_na_raiz()
    pf.checar_scripts_bloqueados()
    assert sorted(p.name for p in tmp_path.iterdir()) == antes


@_SO_WINDOWS
def test_cli_nao_altera_nada():
    # O primeiro cuidado e Windows: `.venv\Scripts\python.exe` e um caminho
    # do Windows. O segundo e o runner do GitHub: ele roda em
    # `windows-latest`, mas NAO tem `.venv` — o workflow instala as
    # dependencias direto no interpretador do runner. apontar para
    # `.venv\Scripts\python.exe` dava `WinError 2` mesmo com o SO certo.
    #
    # `sys.executable` resolve os dois: e o interpretador que esta rodando
    # os testes, entao existe por definicao. Local usa o venv; o CI usa o
    # Python do runner. O que este teste quer verificar — o preflight nao
    # altera nada e devolve JSON — vale nos dois.
    interpretador = Path(sys.executable)
    assert interpretador.exists(), f"interpretador em uso nao existe: {interpretador}"
    proc = subprocess.run(
        [str(interpretador), "scripts/preflight.py", "--json"],
        cwd=pf.ROOT, capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode in (0, 1), proc.stderr
    assert '"ok"' in proc.stdout
