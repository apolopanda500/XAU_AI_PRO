"""Auditoria operacional sem segredos."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
SENSITIVE={'api_key','api_secret','secret','password','token','signature'}
def record(path: Path, *, action: str, payload: dict, status: str) -> dict:
    event={'at':datetime.now(timezone.utc).isoformat(),'action':action,'request_id':payload.get('request_id'),'account_id':payload.get('account_id'),'broker':payload.get('broker'),'market':payload.get('market'),'symbol':payload.get('symbol'),'status':status}
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as handle: handle.write(json.dumps(event,ensure_ascii=False)+'\n')
    return event
