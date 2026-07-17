"""집계 통계: 의원 순위 / 정당별 / 연도별 / 키워드 TOP20."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from .collect import primary_proposer_name
from .models import BillRecord

_STOPWORDS = {
    "관한", "법률", "일부", "개정", "법률안", "위한", "대한", "관련", "등에",
    "그리고", "또는", "위원회", "국회", "정부", "제정",
}
_TOKEN_RE = re.compile(r"[가-힣]{2,}")


def proposer_rankings(bills: list[BillRecord]) -> list[dict]:
    lead_count: Counter[str] = Counter()
    co_count: Counter[str] = Counter()
    party_of: dict[str, str] = {}
    bills_of: dict[str, list[BillRecord]] = defaultdict(list)

    for b in bills:
        name = primary_proposer_name(b.lead_proposer)
        if not name:
            continue
        lead_count[name] += 1
        party_of.setdefault(name, b.party)
        bills_of[name].append(b)

        if b.co_proposers:
            for co_name in re.split(r"[,\s]+", b.co_proposers):
                co_name = co_name.strip()
                if co_name and co_name != name:
                    co_count[co_name] += 1

    rows = []
    for name, cnt in lead_count.most_common():
        rep_bill = max(bills_of[name], key=lambda b: b.propose_dt)
        rows.append(
            {
                "member": name,
                "party": party_of.get(name, ""),
                "lead_count": cnt,
                "co_count": co_count.get(name, 0),
                "rep_bill": rep_bill.bill_name,
            }
        )
    for i, row in enumerate(rows, start=1):
        row["rank"] = i
    return rows


def party_stats(bills: list[BillRecord]) -> list[dict]:
    total: Counter[str] = Counter()
    china: Counter[str] = Counter()
    foreign: Counter[str] = Counter()

    for b in bills:
        party = b.party or "(정당정보없음)"
        total[party] += 1
        if b.category == "China":
            china[party] += 1
        elif b.category == "Foreign":
            foreign[party] += 1

    rows = []
    for party, cnt in total.most_common():
        rows.append({"party": party, "china": china.get(party, 0), "foreign": foreign.get(party, 0), "total": cnt})
    return rows


def yearly_stats(bills: list[BillRecord]) -> list[dict]:
    china: Counter[str] = Counter()
    foreign: Counter[str] = Counter()
    total: Counter[str] = Counter()

    for b in bills:
        year = b.year or "(연도미상)"
        total[year] += 1
        if b.category == "China":
            china[year] += 1
        elif b.category == "Foreign":
            foreign[year] += 1

    rows = []
    for year in sorted(total.keys()):
        rows.append({"year": year, "china": china.get(year, 0), "foreign": foreign.get(year, 0), "total": total[year]})
    return rows


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text or "") if t not in _STOPWORDS]


def top_keywords(bills: list[BillRecord], top_n: int = 20) -> list[dict]:
    """TF-IDF 근사치로 상위 키워드를 추출한다 (외부 의존성 없이 순수 파이썬 구현).

    문서 = 의안 1건(제목+제안이유+주요내용+의안요약). TF는 문서 내 등장 횟수,
    IDF는 log(N / df)로 계산해 문서빈도가 낮을수록(특이할수록) 가중치를 준다.
    """
    docs: list[list[str]] = []
    for b in bills:
        text = " ".join([b.bill_name, b.propose_reason, b.main_content, b.summary])
        docs.append(_tokenize(text))

    df: Counter[str] = Counter()
    for tokens in docs:
        df.update(set(tokens))

    n_docs = max(len(docs), 1)
    score: Counter[str] = Counter()
    for tokens in docs:
        tf = Counter(tokens)
        for term, count in tf.items():
            idf = math.log(n_docs / (1 + df[term])) + 1
            score[term] += count * idf

    return [{"keyword": kw, "score": round(s, 2)} for kw, s in score.most_common(top_n)]
