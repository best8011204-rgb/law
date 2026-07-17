"""마크다운 보고서 생성 (①~⑥ + 요약)."""

from __future__ import annotations

from .keywords import ALL_KEYWORDS
from .models import BillRecord
from .stats import party_stats, proposer_rankings, top_keywords, yearly_stats


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _bill_rows(bills: list[BillRecord]) -> list[list[str]]:
    return [
        [b.bill_no or b.bill_id, b.bill_name, b.lead_proposer, b.party, b.propose_dt, b.proc_result]
        for b in sorted(bills, key=lambda x: x.propose_dt, reverse=True)
    ]


def generate_report(bills: list[BillRecord]) -> str:
    china_bills = [b for b in bills if b.category == "China"]
    foreign_bills = [b for b in bills if b.category == "Foreign"]

    rankings = proposer_rankings(bills)
    parties = party_stats(bills)
    years = yearly_stats(bills)
    keywords = top_keywords(bills, 20)

    parts = []
    parts.append("# 국회 의안 중국/외국 관련성 분석 보고서\n")

    parts.append("## ① 의원 순위\n")
    parts.append(
        _md_table(
            ["순위", "의원", "정당", "대표발의", "공동발의", "대표 법안"],
            [[r["rank"], r["member"], r["party"], r["lead_count"], r["co_count"], r["rep_bill"]] for r in rankings],
        )
    )

    parts.append("\n\n## ② 정당별 통계\n")
    parts.append(
        _md_table(
            ["정당", "China", "Foreign", "Total"],
            [[p["party"], p["china"], p["foreign"], p["total"]] for p in parties],
        )
    )

    parts.append("\n\n## ③ 연도별 통계\n")
    parts.append(
        _md_table(
            ["연도", "China", "Foreign", "Total"],
            [[y["year"], y["china"], y["foreign"], y["total"]] for y in years],
        )
    )

    parts.append("\n\n## ④ 키워드 TOP20\n")
    parts.append(
        _md_table(
            ["순위", "키워드", "점수(TF-IDF 근사)"],
            [[i + 1, k["keyword"], k["score"]] for i, k in enumerate(keywords)],
        )
    )

    parts.append("\n\n## ⑤ China 분류 법안 목록\n")
    parts.append(_md_table(["의안번호", "의안명", "대표발의자", "정당", "발의일", "처리상태"], _bill_rows(china_bills)))

    parts.append("\n\n## ⑥ Foreign 분류 법안 목록\n")
    parts.append(_md_table(["의안번호", "의안명", "대표발의자", "정당", "발의일", "처리상태"], _bill_rows(foreign_bills)))

    parts.append("\n\n## 요약\n")
    parts.append(f"- 검색한 총 법안 수: {len(bills)}")
    parts.append(f"- China 분류 수: {len(china_bills)}")
    parts.append(f"- Foreign 분류 수: {len(foreign_bills)}")
    parts.append(f"- 사용한 검색 키워드: {', '.join(ALL_KEYWORDS)}")
    parts.append(f"- 중복 제거 건수: 의안번호(BILL_ID) 기준 중복 제거 적용, 최종 고유 건수 {len(bills)}건")
    parts.append(
        "- 분류 기준: 중국 관련 키워드가 하나라도 매칭되면 China, 중국 키워드 없이 "
        "외국 관련 키워드만 매칭되면 Foreign, 둘 다 없으면 미분류(목록 제외)"
    )

    return "\n".join(parts) + "\n"
