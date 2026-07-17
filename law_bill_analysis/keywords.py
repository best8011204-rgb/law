"""분류에 사용하는 키워드 목록과 분류 로직."""

from __future__ import annotations

from dataclasses import dataclass, field

CHINA_KEYWORDS = [
    "중국",
    "중화인민공화국",
    "중국산",
    "중국인",
    "중국기업",
    "중국정부",
    "중국공산당",
    "대만",
    "홍콩",
    "마카오",
    "일대일로",
    "화교",
]

FOREIGN_KEYWORDS = [
    "외국",
    "외국인",
    "외국정부",
    "외국기업",
    "해외",
    "국제",
    "수입",
    "수출",
    "FTA",
    "자유무역협정",
    "국제협력",
    "국가안보",
    "경제안보",
]

ALL_KEYWORDS = CHINA_KEYWORDS + FOREIGN_KEYWORDS

# 검색 대상 필드 (BillRecord의 속성명)
SEARCH_FIELDS = [
    "bill_name",
    "propose_reason",
    "main_content",
    "summary",
    "lead_proposer",
    "co_proposers",
]


@dataclass
class ClassificationResult:
    category: str | None  # "China" | "Foreign" | None
    matched_china: list[str] = field(default_factory=list)
    matched_foreign: list[str] = field(default_factory=list)


def _find_matches(text: str, keywords: list[str]) -> list[str]:
    if not text:
        return []
    return [kw for kw in keywords if kw in text]


def classify_bill(field_values: dict[str, str]) -> ClassificationResult:
    """제목/제안이유/주요내용/의안요약/발의자 전체 텍스트를 대상으로 분류한다.

    규칙(사용자 프롬프트 원문 기준):
      - 중국 관련 키워드가 하나라도 등장하면 category = China
      - 중국 키워드 없이 외국 관련 키워드만 등장하면 category = Foreign
      - "외국"이라는 단어만 있다고 자동으로 China로 분류하지 않는다
        (China는 오직 CHINA_KEYWORDS 매칭 여부로만 판정)
    """
    combined = "\n".join(field_values.get(f, "") or "" for f in SEARCH_FIELDS)

    china_hits = _find_matches(combined, CHINA_KEYWORDS)
    foreign_hits = _find_matches(combined, FOREIGN_KEYWORDS)

    if china_hits:
        return ClassificationResult("China", china_hits, foreign_hits)
    if foreign_hits:
        return ClassificationResult("Foreign", china_hits, foreign_hits)
    return ClassificationResult(None, china_hits, foreign_hits)
