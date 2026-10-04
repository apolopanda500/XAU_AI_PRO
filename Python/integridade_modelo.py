# -*- coding: utf-8 -*-
"""Integridade do artefato `.pkl`: SHA-256 gravado no treino, conferido na carga.

POR QUE ISTO EXISTE
===================
`joblib.load()` desserializa com `pickle`, e `pickle` EXECUTA codigo ao
deserializar. O CodeQL classifica isso como `py/unsafe-deserialization`
(critical) — e com razao.

A defesa de caminho ja existe em dois niveis (`_nome_de_artefato` barra a
entrada e `_caminho_confinado` barra o destino), entao um simbolo vindo da
requisicao HTTP nao consegue apontar para um arquivo fora da pasta. MAS
restava um buraco: **quem consegue GRAVAR um `.pkl` dentro da pasta de modelos
ganha execucao de codigo arbitrario**. O confinement de caminho nao diz nada
sobre o CONTEUDO do arquivo.

Isto fecha esse buraco sem trocar a tecnologia:
  - o treino grava o SHA-256 do `.pkl` dentro do `.meta.json`
  - a inferencia recalcula e compara antes de carregar
  - divergencia = recusa COM MOTIVO, e o arquivo nao e desserializado

Por que isso e suficiente aqui
-----------------------------
O modelo e treinado localmente, na propria maquina, e versionado no git. O
modelo que roda e exatamente o que foi treinado aqui. A defesa nao e
criptografia contra um atacante com escrita no disco — e contra troca de
arquivo, erro de copia e artefato veio de outra maquina.

O QUE NAO E FEITO
==================
Nao ha assinatura digital. Isso exigiria chave privada fora do repositorio e
um fluxo de assinatura por build, que e desproporcional para um modelo
treinado na propria maquina. A verificacao pega o ataque de substituir o
arquivo; nao pega um atacante que tambem reescreva o `.meta.json`.

Modelos ja gravados sem o campo `model_sha256` **continuam carregando**:
ausencia de hash e ausencia de verificacao, e a inferencia avisa uma vez.
Remover o modelo antigo e retreinar e o que ativa a checagem de verdade.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

#: Campo no `.meta.json` com o SHA-256 do `.pkl`.
CAMPO = "model_sha256"


def sha256_do_artefato(caminho: Path) -> str:
    """SHA-256 do arquivo, em hexadecimal minusculo.

    Le em blocos: um `.pkl` de 200 MB nao pode ser lido inteiro na memoria
    so para calcular 32 bytes de digest.
    """
    digest = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def conferir(caminho_pkl: Path, meta: dict) -> tuple[bool, str]:
    """Confere o `.pkl` contra o hash gravado no `.meta.json`.

    Devolve (ok, motivo). Motivo vazio quando ok.
    """
    if not caminho_pkl.exists():
        return False, "artefato do modelo nao existe"
    esperado = str(meta.get(CAMPO) or "").strip().lower()
    if not esperado:
        # Modelo treinado antes desta verificacao existir. Nao e recusa: e
        # ausencia de verificacao, e bloquear aqui derrubaria a operacao de
        # 36 modelos ja treinados sem nenhum ganho de seguranca.
        return True, ""
    try:
        atual = sha256_do_artefato(caminho_pkl)
    except OSError as exc:
        return False, f"nao foi possivel ler o artefato: {exc}"
    if atual != esperado:
        return False, (
            f"artefato adulterado: sha256 {atual[:12]} diferente do gravado "
            f"{esperado[:12]}. O modelo nao foi carregado."
        )
    return True, ""


def registrar(caminho_pkl: Path, meta: dict) -> dict:
    """Grava o SHA-256 no `.meta.json` e devolve o dicionario atualizado."""
    meta[CAMPO] = sha256_do_artefato(caminho_pkl)
    return meta