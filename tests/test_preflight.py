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

import pytest

from scripts import preflight as pf


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
    assert pf.checar_mql5().estado == pf.ESTADOS["ok"]


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


def test_cli_nao_altera_nada():
    proc = subprocess.run(
        [str(pf.ROOT / ".venv" / "Scripts" / "python.exe"), "scripts/preflight.py", "--json"],
        cwd=pf.ROOT, capture_output=True, text=True, timeout=180, check=False,
    )
    assert proc.returncode in (0, 1)
    assert '"ok"' in proc.stdout
