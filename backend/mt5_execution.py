"""Adaptador MT5. A chamada real deve ser feita pelo EA/gateway autorizado."""
from __future__ import annotations
import os
class MT5ExecutionError(RuntimeError): pass
class MT5ExecutionAdapter:
    def prepare(self, *, symbol, side, order_type, quantity, price=None, request_id, confirm, available=None):
        if not request_id or not confirm: raise MT5ExecutionError('request_id e confirmação manual são obrigatórios')
        if not symbol or side.lower() not in {'buy','sell'} or quantity<=0: raise MT5ExecutionError('símbolo, lado ou quantidade inválidos')
        if available is not None and quantity>available: raise MT5ExecutionError('volume excede disponibilidade')
        return {'symbol':symbol.upper(),'side':side.lower(),'order_type':order_type.lower(),'volume':quantity,'price':price,'request_id':request_id}
    def execute(self, order, *, explicit_authorization):
        if not explicit_authorization: raise MT5ExecutionError('autorização explícita ausente')
        if os.getenv('XAU_ENABLE_MT5_EXECUTION','0')!='1': return {'ok':False,'status':'blocked','reason':'execução MT5 desativada por padrão','order':order,'withdrawals_enabled':False}
        raise MT5ExecutionError('envio MT5 depende de confirmação do EA e reconciliação de ticket')
