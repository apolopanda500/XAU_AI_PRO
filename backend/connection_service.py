"""Cadastro e validação de conexões por consultas de leitura, sem enviar ordens."""
from backend import connection_store as store
from backend.binance_client import BinanceClient
from backend.mexc_client import MexcClient


def save(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Informe um objeto de conexão.")
    fields = ("id", "broker", "market", "api_key", "api_secret")
    if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in fields):
        raise ValueError("Nome, corretora, mercado, API key e secret são obrigatórios para exchanges.")
    broker, market = payload["broker"].lower(), payload["market"].lower()
    if broker not in {"binance", "mexc"}:
        raise ValueError("MT5 usa a sessão do terminal; não cadastre API key para MT5.")
    if market not in {"crypto-spot", "crypto-futures"}:
        raise ValueError("Selecione Spot ou Futuros para a exchange.")
    store.save_connection(payload["id"], broker, market, payload["api_key"].strip(), payload["api_secret"].strip())
    return {"ok": True, "validated": False}


def action(connection_id: str, command: str) -> dict:
    if command not in {"test", "activate", "deactivate"}:
        raise LookupError("Comando de conexão não encontrado.")
    item = next((row for row in store.list_connections() if row["id"] == connection_id), None)
    if item is None:
        raise LookupError("Conexão não encontrada.")
    if item["broker"] not in {"mexc", "binance"}:
        raise ValueError("Sincronize MT5 pela sessão do terminal.")
    if command == "deactivate":
        store.set_connection_active(connection_id, False)
        return {"ok": True, "active": False}
    key, secret = store.load_connection_credentials(connection_id)
    market = "futures" if item["market"] == "crypto-futures" else "spot"
    if item["broker"] == "binance":
        client = BinanceClient(market)
        client.api_key, client.secret = key, secret
    else:
        client = MexcClient(market)
        client.api_key, client.api_secret = key, secret
    # Consulta autenticada da conta exata, sem alterar o ambiente global.
    result = client.account()
    if not isinstance(result, (dict, list)) or (isinstance(result, dict) and result.get("success") is False):
        raise ValueError("Resposta inválida da corretora.")
    if command == "activate":
        store.set_connection_active(connection_id, True)
    return {"ok": True, "validated": True, "read_only": True}
