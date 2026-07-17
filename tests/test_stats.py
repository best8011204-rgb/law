import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from law_bill_analysis.models import BillRecord
from law_bill_analysis.stats import party_stats, proposer_rankings, top_keywords, yearly_stats


def _bill(**kwargs) -> BillRecord:
    base = dict(
        bill_id="1",
        bill_no="1",
        bill_name="테스트법",
        lead_proposer="홍길동의원 등 10인",
        co_proposers="김철수 이영희",
        party="더불어민주당",
        propose_dt="2025-03-01",
        propose_reason="중국산 수입품 규제를 위한",
        main_content="",
        summary="",
        proc_result="",
        category="China",
        matched_keywords=["중국산"],
    )
    base.update(kwargs)
    return BillRecord(**base)


def test_proposer_rankings_counts_lead_and_co():
    bills = [_bill(bill_id="1"), _bill(bill_id="2", lead_proposer="김철수의원 등 5인")]
    rankings = proposer_rankings(bills)
    hong = next(r for r in rankings if r["member"] == "홍길동")
    assert hong["lead_count"] == 1
    kim = next(r for r in rankings if r["member"] == "김철수")
    assert kim["co_count"] == 1  # bill 1의 공동발의자로 등장


def test_party_stats_splits_china_foreign():
    bills = [_bill(bill_id="1", category="China"), _bill(bill_id="2", category="Foreign")]
    rows = party_stats(bills)
    assert rows[0]["party"] == "더불어민주당"
    assert rows[0]["china"] == 1
    assert rows[0]["foreign"] == 1
    assert rows[0]["total"] == 2


def test_yearly_stats_groups_by_year():
    bills = [_bill(bill_id="1", propose_dt="2024-01-01"), _bill(bill_id="2", propose_dt="2025-01-01")]
    rows = yearly_stats(bills)
    years = [r["year"] for r in rows]
    assert years == ["2024", "2025"]


def test_top_keywords_returns_ranked_list():
    bills = [_bill(bill_id="1", bill_name="중국산 수입 규제법"), _bill(bill_id="2", bill_name="중국산 관세법")]
    result = top_keywords(bills, top_n=5)
    assert any(k["keyword"] == "중국산" for k in result)
