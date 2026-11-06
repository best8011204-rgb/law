#!/usr/bin/env python3
"""data/raw.jsonl 로부터 기관·연구자(그룹 리더) 영향력 지표 산출."""
import json, re, sys
from collections import defaultdict
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "analysis"

works = [json.loads(l) for l in open(RAW, encoding="utf-8")]
# 연도별 평균 인용 → 연도 정규화 인용(1.0 = 같은 해 평균)
wy = pd.DataFrame([(w["id"], w["publication_year"], w["cited_by_count"]) for w in works],
                  columns=["wid", "year", "cites"])
ymean = wy.groupby("year")["cites"].mean()
wy["ncites"] = wy["cites"] / wy["year"].map(ymean).replace(0, 1)
W = wy.set_index("wid")

def norm_inst(name):
    # 'Intel (United States)', 'Intel (Malaysia)' → 'Intel'; 기업 자회사 통합용
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()

ALIASES = {"Samsung": "Samsung Electronics"}
SPLIT_BY_COUNTRY = {"Institute of Microelectronics"}

def hindex(c):
    c = sorted(c, reverse=True)
    return sum(1 for i, x in enumerate(c, 1) if x >= i)

inst_w = defaultdict(set); inst_type = {}; inst_cc = defaultdict(set)
auth_w = defaultdict(set); auth_last = defaultdict(set); auth_first = defaultdict(set); auth_name = {}; auth_inst = defaultdict(lambda: defaultdict(int))
for w in works:
    seen = set()
    for a in w.get("authorships") or []:
        au = a.get("author") or {}
        aid = au.get("id")
        insts = a.get("institutions") or []
        for i in insts:
            if not i.get("display_name"):
                continue
            key = norm_inst(i["display_name"]) if i.get("type") == "company" else i["display_name"]
            key = ALIASES.get(key, key)
            if key in SPLIT_BY_COUNTRY:  # 동명 기관 분리 (예: A*STAR IME vs CAS IME)
                key = f"{key} [{i.get('country_code') or '?'}]"
            inst_w[key].add(w["id"]); inst_type[key] = i.get("type")
            if i.get("country_code"): inst_cc[key].add(i["country_code"])
            seen.add(key)
            if aid: auth_inst[aid][key] += 1
        if aid:
            auth_name[aid] = au.get("display_name")
            auth_w[aid].add(w["id"])
            if a.get("author_position") == "first":
                auth_first[aid].add(w["id"])
            if a.get("author_position") == "last":
                auth_last[aid].add(w["id"])

def metrics(ws):
    sub = W.loc[list(ws)]
    return dict(papers=len(sub), cites=int(sub.cites.sum()), h=hindex(sub.cites),
                ncites_sum=round(sub.ncites.sum(), 1), ncites_mean=round(sub.ncites.mean(), 2),
                recent_23_26=int((sub.year >= 2023).sum()))

rows = []
for k, ws in inst_w.items():
    if len(ws) < 5: continue
    rows.append(dict(institution=k, type=inst_type[k], countries=";".join(sorted(inst_cc[k])), **metrics(ws)))
inst = pd.DataFrame(rows)
# 종합 점수: h-index, 정규화인용합, 논문수의 백분위 평균
for c in ["h", "ncites_sum", "papers"]:
    inst[c + "_pct"] = inst[c].rank(pct=True)
inst["score"] = ((inst.h_pct + inst.ncites_sum_pct + inst.papers_pct) / 3).round(3)
inst = inst.sort_values(["score", "ncites_sum"], ascending=False).drop(columns=[c for c in inst if c.endswith("_pct")])
inst.to_csv(f"{OUT}/institutions.csv", index=False, encoding="utf-8-sig")

rows = []
for aid, ws in auth_w.items():
    if len(ws) < 4: continue
    m = metrics(ws)
    main_inst = max(auth_inst[aid].items(), key=lambda x: x[1])[0] if auth_inst[aid] else ""
    rows.append(dict(author=auth_name[aid], author_id=aid, main_institution=main_inst,
                     first_author_papers=len(auth_first[aid]), last_author_papers=len(auth_last[aid]), **m))
au = pd.DataFrame(rows).sort_values(["h", "ncites_sum"], ascending=False)
au.to_csv(f"{OUT}/authors.csv", index=False, encoding="utf-8-sig")

# 기관 상위 그룹의 대표 논문 (정규화 인용 상위 3)
titles = {w["id"]: (w["publication_year"], w["title"]) for w in works}
lines = []
for k in inst.institution.head(15):
    top = W.loc[list(inst_w[k])].sort_values("ncites", ascending=False).head(3)
    lines.append(f"## {k}")
    for wid, r in top.iterrows():
        y, t = titles[wid]
        lines.append(f"- ({y}, 인용 {int(r.cites)}) {t}")
open(f"{OUT}/top_institution_papers.md", "w", encoding="utf-8").write("\n".join(lines))

pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 45)
print(inst.head(25).to_string(index=False))
print()
print(au.head(30).to_string(index=False, columns=["author","main_institution","papers","first_author_papers","last_author_papers","cites","h","ncites_sum","recent_23_26"]))
