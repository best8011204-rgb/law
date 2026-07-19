"""여러 서비스ID/파라미터 조합을 시도해 실제로 동작하는 것을 찾는 1회성 진단 스크립트."""

import json
import os

import requests

KEY = os.environ["ASSEMBLY_API_KEY"]
BASE = "https://open.assembly.go.kr/portal/openapi"

CANDIDATES = [
    ("ALLBILL", {"AGE": "22"}),
    ("ALLBILL", {}),
    ("TVBPMBILL11", {"AGE": "22"}),
    ("TVBPMBILL11", {}),
    ("BILLINFOLIST", {"AGE": "22"}),
]

for service_id, extra in CANDIDATES:
    params = {"KEY": KEY, "Type": "json", "pIndex": 1, "pSize": 1, **extra}
    try:
        resp = requests.get(f"{BASE}/{service_id}", params=params, timeout=15)
        body = resp.text[:800]
    except Exception as exc:
        body = f"EXC: {exc}"
    print(f"=== {service_id} extra={extra} status={getattr(resp, 'status_code', '?')} ===")
    print(body)
    print()
