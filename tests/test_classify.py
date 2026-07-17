import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from law_bill_analysis.keywords import classify_bill


def test_china_keyword_wins_even_with_foreign_keywords():
    result = classify_bill(
        {
            "bill_name": "대중국 수출 규제 강화를 위한 법률안",
            "propose_reason": "중국산 제품의 수입이 증가함에 따라...",
            "main_content": "",
            "summary": "",
            "lead_proposer": "",
            "co_proposers": "",
        }
    )
    assert result.category == "China"
    assert "중국산" in result.matched_china


def test_foreign_only_without_china():
    result = classify_bill(
        {
            "bill_name": "외국인 근로자 고용 촉진법 일부개정법률안",
            "propose_reason": "외국인 근로자의 처우 개선을 위해",
            "main_content": "",
            "summary": "",
            "lead_proposer": "",
            "co_proposers": "",
        }
    )
    assert result.category == "Foreign"
    assert result.matched_china == []


def test_no_match_returns_none():
    result = classify_bill(
        {
            "bill_name": "도로교통법 일부개정법률안",
            "propose_reason": "교통사고 예방을 위해",
            "main_content": "",
            "summary": "",
            "lead_proposer": "",
            "co_proposers": "",
        }
    )
    assert result.category is None


def test_generic_foreign_word_does_not_force_china():
    result = classify_bill(
        {
            "bill_name": "FTA 이행에 관한 특별법",
            "propose_reason": "자유무역협정 이행을 위해 국제협력을 강화한다",
            "main_content": "",
            "summary": "",
            "lead_proposer": "",
            "co_proposers": "",
        }
    )
    assert result.category == "Foreign"
