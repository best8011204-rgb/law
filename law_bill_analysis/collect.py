"""전체 의안 수집 -> 상세조회 -> 중복제거 -> 분류 파이프라인."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from . import config
from .api_client import AssemblyApiClient
from .detail_fetcher import DetailFetcher
from .keywords import classify_bill
from .member_lookup import build_name_to_party_map
from .models import BillRecord

logger = logging.getLogger(__name__)


def primary_proposer_name(lead_proposer: str) -> str:
    """PROPOSER 필드는 보통 '홍길동의원 등 10인' 형태이므로 대표발의자 이름만 뽑는다."""
    if not lead_proposer:
        return ""
    name = lead_proposer.split("의원")[0].split(",")[0].strip()
    return name


def _row_get(row: dict, key: str) -> str:
    field_name = config.FIELD_MAP[key]
    value = row.get(field_name, "")
    return (value or "").strip()


def _cache_path(age: str) -> Path:
    d = Path(config.CACHE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"bills_age{age}.jsonl"


def _load_cache(path: Path) -> dict[str, BillRecord]:
    records: dict[str, BillRecord] = {}
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            records[data["bill_id"]] = BillRecord(**data)
    return records


def _append_cache(path: Path, record: BillRecord) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def collect_bills(
    age: str = config.DEFAULT_AGE,
    fetch_details: bool = True,
    limit: int | None = None,
    resume: bool = True,
) -> list[BillRecord]:
    """모든 의안을 수집하고(옵션에 따라 상세 스크레이핑 포함) 키워드 분류까지 수행한다.

    resume=True이면 캐시 파일(output/cache/bills_age{age}.jsonl)에 이미 있는
    bill_id는 API/스크레이핑을 다시 호출하지 않고 재사용한다.
    """
    client = AssemblyApiClient()
    detail_fetcher = DetailFetcher() if fetch_details else None
    name_to_party = build_name_to_party_map()

    cache_path = _cache_path(age)
    cached = _load_cache(cache_path) if resume else {}

    extra_params: dict = {}
    if age and age.lower() != "all":
        extra_params[config.FIELD_MAP["age"]] = age

    seen: dict[str, BillRecord] = dict(cached)
    count = 0

    for row in client.fetch_all(config.BILL_LIST_SERVICE_ID, extra_params=extra_params):
        bill_id = _row_get(row, "bill_id") or _row_get(row, "bill_no")
        if not bill_id:
            continue

        if bill_id in seen:
            count += 1
            if limit and count >= limit:
                break
            continue

        record = BillRecord(
            bill_id=bill_id,
            bill_no=_row_get(row, "bill_no"),
            bill_name=_row_get(row, "bill_name"),
            lead_proposer=_row_get(row, "proposer"),
            co_proposers=_row_get(row, "publ_proposer"),
            propose_dt=_row_get(row, "propose_dt"),
            committee=_row_get(row, "committee"),
            proc_result=_row_get(row, "proc_result"),
            detail_link=_row_get(row, "detail_link"),
            age=_row_get(row, "age") or age,
        )
        record.party = name_to_party.get(primary_proposer_name(record.lead_proposer), "")

        if detail_fetcher is not None:
            try:
                details = detail_fetcher.fetch(record.detail_link)
                record.propose_reason = details.get("propose_reason", "")
                record.main_content = details.get("main_content", "")
                record.summary = details.get("summary", "")
            except Exception as exc:  # 네트워크/파싱 실패는 건너뛰고 계속 진행
                logger.warning("상세조회 실패 bill_id=%s: %s", bill_id, exc)

        result = classify_bill(
            {
                "bill_name": record.bill_name,
                "propose_reason": record.propose_reason,
                "main_content": record.main_content,
                "summary": record.summary,
                "lead_proposer": record.lead_proposer,
                "co_proposers": record.co_proposers,
            }
        )
        record.category = result.category
        record.matched_keywords = sorted(set(result.matched_china + result.matched_foreign))

        seen[bill_id] = record
        _append_cache(cache_path, record)

        count += 1
        if limit and count >= limit:
            break

    return list(seen.values())
