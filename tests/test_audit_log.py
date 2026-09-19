import json
from backend.audit_log import record

def test_audit_records_metadata_without_secrets(tmp_path):
    path=tmp_path/'audit.jsonl'
    event=record(path,action='order',payload={'request_id':'r1','account_id':'a1','broker':'mexc','market':'spot','symbol':'BTCUSDT','api_secret':'never'},status='blocked')
    assert event['status']=='blocked'
    saved=json.loads(path.read_text(encoding='utf-8'))
    assert saved['request_id']=='r1'
    assert 'api_secret' not in saved
