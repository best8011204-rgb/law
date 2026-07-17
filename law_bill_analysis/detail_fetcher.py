"""의안 상세페이지(제안이유/주요내용/의안요약) 스크레이핑.

열린국회정보 OpenAPI의 의안 목록 서비스(ALLBILL 등)는 제안이유/주요내용/의안요약을
필드로 제공하지 않는다. 이 정보는 목록 항목의 DETAIL_LINK가 가리키는 의안 상세
페이지(likms.assembly.go.kr)의 HTML에만 존재하므로, 여기서는 해당 페이지를 받아
"제안이유", "주요내용", "제안경위"/"검토보고서" 등 알려진 섹션 헤더를 기준으로
텍스트를 잘라낸다.

주의: 이 파서는 네트워크가 없는 환경에서 실제 페이지로 검증하지 못했다. 사이트
HTML 구조가 예상과 다르면 빈 문자열을 반환하도록 방어적으로 작성했으며, 실제 값이
비어 있는 채 계속 나온다면 `_SECTION_HEADERS`와 파싱 로직을 실제 페이지에 맞게
조정해야 한다.
"""

from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from . import config

_SECTION_HEADERS = {
    "propose_reason": ["제안이유"],
    "main_content": ["주요내용", "주요 내용"],
    "summary": ["의안요약", "제안요지"],
}

_ALL_HEADERS = [h for hs in _SECTION_HEADERS.values() for h in hs] + [
    "참고사항",
    "비고",
    "부칙",
    "검토보고서",
    "제안경위",
]


def _extract_sections(full_text: str) -> dict[str, str]:
    result = {key: "" for key in _SECTION_HEADERS}
    for key, headers in _SECTION_HEADERS.items():
        for header in headers:
            idx = full_text.find(header)
            if idx == -1:
                continue
            start = idx + len(header)
            end = len(full_text)
            for other in _ALL_HEADERS:
                if other == header:
                    continue
                pos = full_text.find(other, start)
                if pos != -1:
                    end = min(end, pos)
            snippet = full_text[start:end].strip(" \t\n:：-")
            if snippet:
                result[key] = snippet
                break
    return result


class DetailFetcher:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    def fetch(self, detail_link: str) -> dict[str, str]:
        if not detail_link:
            return {"propose_reason": "", "main_content": "", "summary": ""}

        last_error: Exception | None = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = self.session.get(detail_link, timeout=config.REQUEST_TIMEOUT_SEC)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_BACKOFF_BASE_SEC * (2 ** (attempt - 1)))
        else:
            raise last_error  # type: ignore[misc]

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = re.sub(r"[ \t]+", " ", soup.get_text("\n"))
        text = re.sub(r"\n{2,}", "\n", text)

        time.sleep(config.REQUEST_INTERVAL_SEC)
        return _extract_sections(text)
