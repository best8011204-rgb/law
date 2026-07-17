from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class BillRecord:
    bill_id: str
    bill_no: str = ""
    bill_name: str = ""
    lead_proposer: str = ""
    co_proposers: str = ""
    party: str = ""
    propose_dt: str = ""
    propose_reason: str = ""
    main_content: str = ""
    summary: str = ""
    committee: str = ""
    proc_result: str = ""
    detail_link: str = ""
    age: str = ""
    category: str | None = None
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def year(self) -> str:
        if self.propose_dt and len(self.propose_dt) >= 4:
            return self.propose_dt[:4]
        return ""

    def to_dict(self) -> dict:
        return asdict(self)
