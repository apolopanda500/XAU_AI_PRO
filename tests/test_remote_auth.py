"""Cobertura de segurança de backend/remote_auth.py.

Este modulo emite o token de sessao que o app Android usa para falar com o
gateway remoto, entao e a fronteira de confianca do modo mobile. Nao pode ter
cobertura zero.

O banco e sempre um arquivo temporario: o teste nunca toca em
backend/auth.sqlite3, que em producao guarda hashes de senha e tokens.
"""
import hashlib
import sqlite3
import time

import pytest

from backend import remote_auth

SENHA = "senha-de-teste-bem-longa"


@pytest.fixture(autouse=True)
def _db_isolado(tmp_path, monkeypatch):
    """Cada teste roda contra um sqlite proprio e um TTL controlado."""
    monkeypatch.setattr(remote_auth, "DB_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(remote_auth, "SESSION_TTL", 3600)
    yield


# --------------------------------------------------------------------------
# cadastro
# --------------------------------------------------------------------------

def test_registro_cria_usuario_e_aceita_login():
    user_id = remote_auth.register("Trader@Exemplo.com", SENHA)
    assert user_id > 0
    token, login_id = remote_auth.login("trader@exemplo.com", SENHA)
    assert login_id == user_id
    assert token


def test_registro_normaliza_email_e_rejeita_duplicado():
    remote_auth.register("Trader@Exemplo.com", SENHA)
    with pytest.raises(ValueError, match="já cadastrado"):
        remote_auth.register("TRADER@exemplo.com", SENHA)


def test_registro_exige_senha_com_12_caracteres():
    with pytest.raises(ValueError, match="12 caracteres"):
        remote_auth.register("trader@exemplo.com", "curta123")


@pytest.mark.parametrize("email", ["sem-arroba", "", "a" * 250 + "@x.com"])
def test_registro_rejeita_email_invalido(email):
    with pytest.raises(ValueError, match="email"):
        remote_auth.register(email, SENHA)


# --------------------------------------------------------------------------
# senha: nunca em texto plano, e comparacao constante
# --------------------------------------------------------------------------

def test_senha_e_guardada_com_hash_scrypt_e_salt():
    remote_auth.register("trader@exemplo.com", SENHA)
    with sqlite3.connect(remote_auth.DB_PATH) as db:
        stored = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored.startswith("scrypt$")
    assert SENHA not in stored
    # scrypt$<16 bytes de salt em hex>$<64 bytes de digest em hex>
    # n=2**14, r=8, p=1 => 128 * r * p = 1024 bytes de saida bruta, mas
    # hashlib.scrypt sem length usa dklen=64 (32 em hex seria metade).
    _, salt_hex, digest_hex = stored.split("$")
    assert len(salt_hex) == 32
    assert len(digest_hex) == 128


def test_senhas_diferentes_geram_salt_e_digest_diferentes():
    remote_auth.register("a@exemplo.com", SENHA)
    remote_auth.register("b@exemplo.com", SENHA)
    with sqlite3.connect(remote_auth.DB_PATH) as db:
        hashes = [row[0] for row in db.execute("SELECT password_hash FROM users")]
    assert hashes[0] != hashes[1]


# --------------------------------------------------------------------------
# login
# --------------------------------------------------------------------------

def test_login_recusa_senha_errada():
    remote_auth.register("trader@exemplo.com", SENHA)
    with pytest.raises(PermissionError, match="credenciais"):
        remote_auth.login("trader@exemplo.com", SENHA + "x")


def test_login_recusa_usuario_inexistente():
    with pytest.raises(PermissionError, match="credenciais"):
        remote_auth.login("ninguem@exemplo.com", SENHA)


def test_login_nao_divulgue_se_o_usuario_existe():
    """Mensagem identica para usuario inexistente e senha errada.

    Sem isso, o login vaza um orcario de emails validos.
    """
    remote_auth.register("trader@exemplo.com", SENHA)
    with pytest.raises(PermissionError) as inexistente:
        remote_auth.login("ninguem@exemplo.com", SENHA)
    with pytest.raises(PermissionError) as senha_errada:
        remote_auth.login("trader@exemplo.com", "outra-senha-longa-aqui")
    assert str(inexistente.value) == str(senha_errada.value)


# --------------------------------------------------------------------------
# sessao
# --------------------------------------------------------------------------

def test_token_de_sessao_autentica_o_usuario_correto():
    user_id = remote_auth.register("trader@exemplo.com", SENHA)
    token, _ = remote_auth.login("trader@exemplo.com", SENHA)
    assert remote_auth.authenticate(token) == user_id


def test_token_nao_e_guardado_em_texto_plano():
    remote_auth.register("trader@exemplo.com", SENHA)
    token, _ = remote_auth.login("trader@exemplo.com", SENHA)
    with sqlite3.connect(remote_auth.DB_PATH) as db:
        rows = [row[0] for row in db.execute("SELECT token_hash FROM sessions")]
    assert token not in rows
    assert hashlib.sha256(token.encode()).hexdigest() in rows


def test_autenticar_recusa_token_desconhecido():
    remote_auth.register("trader@exemplo.com", SENHA)
    with pytest.raises(PermissionError, match="sessão"):
        remote_auth.authenticate("token-inventado")


def test_sessao_expirada_e_recusada():
    remote_auth.register("trader@exemplo.com", SENHA)
    token, _ = remote_auth.login("trader@exemplo.com", SENHA)
    assert remote_auth.authenticate(token) > 0
    # empurra a expiracao para o passado
    with sqlite3.connect(remote_auth.DB_PATH) as db:
        db.execute("UPDATE sessions SET expires_at = ?", (int(time.time()) - 1,))
    with pytest.raises(PermissionError, match="expirada"):
        remote_auth.authenticate(token)


def test_logout_invalida_o_token():
    remote_auth.register("trader@exemplo.com", SENHA)
    token, _ = remote_auth.login("trader@exemplo.com", SENHA)
    remote_auth.logout(token)
    with pytest.raises(PermissionError, match="sessão"):
        remote_auth.authenticate(token)


def test_logout_nao_derruba_a_sessao_de_outro_usuario():
    remote_auth.register("a@exemplo.com", SENHA)
    remote_auth.register("b@exemplo.com", SENHA)
    token_a, _ = remote_auth.login("a@exemplo.com", SENHA)
    token_b, _ = remote_auth.login("b@exemplo.com", SENHA)
    remote_auth.logout(token_a)
    with pytest.raises(PermissionError):
        remote_auth.authenticate(token_a)
    assert remote_auth.authenticate(token_b) > 0


def test_logout_de_token_inexistente_nao_levanta():
    remote_auth.logout("token-que-nunca-existiu")
