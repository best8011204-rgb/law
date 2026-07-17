"""대표발의자 이름 -> 정당 매핑 (국회의원 인적사항 API 기반, best-effort).

ALLBILL 류 의안 목록에는 정당 필드가 없는 경우가 많아, 별도 국회의원 인적사항
서비스를 한 번 전체 조회해 이름->정당 딕셔너리를 만든다. 동명이인이 있으면
마지막으로 조회된 값으로 덮어써지므로 완벽하지 않다 (best-effort).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import config
from .api_client import AssemblyApiClient, AssemblyApiError

logger = logging.getLogger(__name__)


def _cache_path() -> Path:
    d = Path(config.CACHE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d / "member_party.json"


def build_name_to_party_map(force_refresh: bool = False) -> dict[str, str]:
    path = _cache_path()
    if path.exists() and not force_refresh:
        return json.loads(path.read_text(encoding="utf-8"))

    mapping: dict[str, str] = {}
    try:
        client = AssemblyApiClient()
        for row in client.fetch_all(config.MEMBER_INFO_SERVICE_ID):
            name = (row.get(config.MEMBER_FIELD_MAP["name"]) or "").strip()
            party = (row.get(config.MEMBER_FIELD_MAP["party"]) or "").strip()
            if name and party:
                mapping[name] = party
    except AssemblyApiError as exc:
        logger.warning("의원 정당 정보 조회 실패, 정당 정보 없이 진행: %s", exc)

    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping
