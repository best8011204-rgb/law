"""열린국회정보 OpenAPI 클라이언트 (제네릭 페이지네이션)."""

from __future__ import annotations

import time
from typing import Any, Iterator

import requests

from . import config


class AssemblyApiError(RuntimeError):
    pass


def _extract_rows_and_total(payload: dict, service_id: str) -> tuple[list[dict], int]:
    """열린국회정보류 OpenAPI의 공통 응답 포맷을 파싱한다.

    표준 포맷: {"<SERVICE_ID>": [{"head": [{"list_total_count": N}, {"RESULT": {...}}]},
                                 {"row": [ {...}, ... ]}]}
    일부 서비스는 오류 시 {"RESULT": {"CODE": "...", "MESSAGE": "..."}} 형태로만 응답한다.
    """
    if "RESULT" in payload and service_id not in payload:
        result = payload["RESULT"]
        raise AssemblyApiError(f"{result.get('CODE')}: {result.get('MESSAGE')}")

    block = payload.get(service_id)
    if not block:
        raise AssemblyApiError(f"응답에 '{service_id}' 키가 없습니다: {list(payload.keys())}")

    rows: list[dict] = []
    total = 0
    for item in block:
        if "head" in item:
            for h in item["head"]:
                if "list_total_count" in h:
                    total = int(h["list_total_count"])
                if "RESULT" in h and h["RESULT"].get("CODE") not in (None, "INFO-000"):
                    raise AssemblyApiError(f"{h['RESULT'].get('CODE')}: {h['RESULT'].get('MESSAGE')}")
        if "row" in item:
            rows.extend(item["row"])
    return rows, total


class AssemblyApiClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or config.API_KEY
        if not self.api_key:
            raise AssemblyApiError(
                "ASSEMBLY_API_KEY가 설정되지 않았습니다. .env 또는 환경변수로 지정하세요."
            )
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    def _get(self, service_id: str, params: dict[str, Any]) -> dict:
        url = f"{config.API_BASE_URL}/{service_id}"
        query = {"KEY": self.api_key, "Type": "json", **params}

        last_error: Exception | None = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=query, timeout=config.REQUEST_TIMEOUT_SEC)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < config.MAX_RETRIES:
                    wait = config.RETRY_BACKOFF_BASE_SEC * (2 ** (attempt - 1))
                    time.sleep(wait)
        raise AssemblyApiError(f"{service_id} 호출 실패 (재시도 {config.MAX_RETRIES}회 소진): {last_error}")

    def fetch_all(
        self,
        service_id: str,
        extra_params: dict[str, Any] | None = None,
        page_size: int | None = None,
    ) -> Iterator[dict]:
        """전체 페이지를 순회하며 row를 하나씩 yield한다."""
        page_size = page_size or config.PAGE_SIZE
        p_index = 1
        seen = 0
        total = None

        while True:
            params = {"pIndex": p_index, "pSize": page_size, **(extra_params or {})}
            payload = self._get(service_id, params)
            rows, reported_total = _extract_rows_and_total(payload, service_id)

            if total is None:
                total = reported_total

            if not rows:
                break

            for row in rows:
                yield row
            seen += len(rows)

            if total and seen >= total:
                break
            p_index += 1
            time.sleep(config.REQUEST_INTERVAL_SEC)
