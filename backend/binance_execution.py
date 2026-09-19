"""Adaptador Binance Spot/Futuros. Envio desligado por padrão."""
from __future__ import annotations
import os
class BinanceExecutionError(RuntimeError): pass
class BinanceExecutionAdapter:
    def __init__(self, market='spot'):
        if market not in {'spot','futures'}: raise ValueError('market inválido')
        self.market=market
    def prepare(self, *, symbol, side, order_type, quantity, price=None, request_id, confirm, available=None):
        if not request_id or not confirm: raise BinanceExecutionError('request_id e confirmação manual são obrigatórios')
        if not symbol or side.lower() not in {'buy','sell'} or quantity<=0: raise BinanceExecutionError('símbolo, lado ou quantidade inválidos')
        if available is not None and quantity>available: raise BinanceExecutionError('saldo insuficiente')
        if order_type.lower()=='limit' and (price is None or price<=0): raise BinanceExecutionError('preço obrigatório')
        return {'symbol':symbol.upper(),'side':side.upper(),'type':order_type.upper(),'quantity':quantity,'price':price,'newClientOrderId':request_id}
    def execute(self, order, *, explicit_authorization):
        if not explicit_authorization: raise BinanceExecutionError('autorização explícita ausente')
        if os.getenv('XAU_ENABLE_BINANCE_EXECUTION','0')!='1': return {'ok':False,'status':'blocked','reason':'execução Binance desativada por padrão','order':order,'withdrawals_enabled':False}
        raise BinanceExecutionError('adaptador Binance pronto, envio controlado ainda não liberado')
