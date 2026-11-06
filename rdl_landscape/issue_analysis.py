#!/usr/bin/env python3
"""인용 상위 그룹별 주요 이슈(제목+초록 키워드 사전) 비중·특화도(lift) 산출."""
import json, re, sys
from collections import defaultdict
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw_filtered.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "analysis_filtered"

# 이슈 사전: 제목+초록 정규식
ISSUES = {
    "미세 L/S·고밀도 배선": r"fine[- ]?(?:pitch|line)|line[/ -]?(?:and[- ])?space|\bl/s\b|sub-?micron|submicrometer|\d\s*(?:µ|μ|u)m\s*/\s*\d|high[- ]density (?:rdl|interconnect|wiring)|io density|damascene",
    "유전체·감광성 소재(PI/PBO)": r"dielectric|polyimide|\bpbo\b|photosensitive|photo-?imageable|\bpid\b|polymer|ajinomoto|\babf\b|low[- ](?:dk|k\b|loss)",
    "Cu 도금·시드·식각 공정": r"electroplat|plating|seed layer|sputter|etch|cmp\b|chemical mechanical|nanotwin|leveler|\bbarrier\b",
    "리소그래피·노광": r"lithograph|stepper|laser direct imag|\bldi\b|exposure|photoresist|depth of focus|i-line|overlay",
    "휨(warpage)·열기계 응력": r"warpage|warping|thermo-?mechanical|stress|cte mismatch|coefficient of thermal expansion",
    "다이 시프트·몰딩·캐리어": r"die shift|die-shift|mold(?:ing)?\b|emc\b|epoxy mold|compression mold|carrier|temporary bond|debond",
    "신뢰성(EM·TC·크랙)": r"electromigration|\bem\b|thermal cycl|reliabilit|crack|delamination|fatigue|drop test|failure",
    "전기 성능(SI/PI·고주파)": r"signal integrity|power integrity|\bsi\b|\bpi\b|insertion loss|crosstalk|impedance|high[- ]speed|ghz|bandwidth|eye diagram|s-parameter",
    "RF·안테나 인 패키지": r"antenna|mmwave|millimeter[- ]wave|\brf\b|5g|6g|radar|\baip\b|d-band|w-band",
    "열 관리": r"thermal management|heat dissipation|thermal resistance|cooling|hot ?spot|junction temperature|heat spread",
    "칩렛·이종집적·HPC/AI": r"chiplet|heterogeneous integration|\bhpc\b|high[- ]performance comput|\bai\b|artificial intelligence|\bhbm\b|\bsoc\b",
    "2.5D/RDL 인터포저·브리지": r"interposer|cowos|2\.[35]d|bridge|\bemib\b|\blsi\b|si-?less|tsv-?less",
    "패널 레벨(FOPLP)": r"panel[- ]level|\bfoplp\b|\bplp\b|panel size|large[- ]panel|\d{3}\s*(?:mm)?\s*[x×]\s*\d{3}",
    "칩 퍼스트/RDL 퍼스트 공정흐름": r"chip[- ]first|die[- ]first|rdl[- ]first|chip[- ]last|face[- ](?:up|down)|mold[- ]first",
    "유리 기판·TGV": r"glass|\btgv\b|through[- ]glass",
    "광패키징·CPO": r"photonic|optical|\bcpo\b|co-packaged optic|waveguide|optical engine",
    "하이브리드 본딩·마이크로범프": r"hybrid bond|cu-cu|cu/cu|direct bond|micro-?bump|\bubm\b|solder joint|flip[- ]chip|bonding",
    "시뮬레이션·설계·라우팅 자동화": r"simulation|finite element|\bfem\b|\bfea\b|modeling|modelling|routing|design automation|\beda\b|machine learning|optimi[sz]ation",
}
RX = {k: re.compile(v, re.I) for k, v in ISSUES.items()}

works = [json.loads(l) for l in open(RAW, encoding="utf-8")]
def txt(w):
    inv = w.get("abstract_inverted_index") or {}
    pos = {i: k for k, idx in inv.items() for i in idx}
    return (w.get("title") or "") + " " + " ".join(pos[i] for i in sorted(pos))

df = pd.DataFrame([dict(wid=w["id"], year=w["publication_year"], cites=w["cited_by_count"],
                        title=w.get("title"), text=txt(w)) for w in works]).set_index("wid")
df["ncites"] = df.cites / df.year.map(df.groupby("year").cites.mean()).replace(0, 1)
for k, r in RX.items():
    df[k] = df.text.str.contains(r)

# 그룹 정의: 기관(정규화명) 또는 저자 기준
def inst_names(w):
    out = set()
    for a in w.get("authorships") or []:
        for i in a.get("institutions") or []:
            n = i.get("display_name") or ""
            out.add((re.sub(r"\s*\([^)]*\)\s*$", "", n), i.get("country_code")))
    return out
def authors(w):
    return {(a.get("author") or {}).get("display_name") for a in w.get("authorships") or []}

GROUPS = {
    "Lau 산업 컨소시엄(ASM·Unimicron·Huawei·HKUST 등)": lambda w: "John Hon-Shing Lau" in authors(w),
    "TSMC": lambda w: any(n == "Taiwan Semiconductor Manufacturing Company" for n, _ in inst_names(w)),
    "Georgia Tech PRC": lambda w: any(n == "Georgia Institute of Technology" for n, _ in inst_names(w)),
    "중국과학원 IME(CN)": lambda w: any(n == "Institute of Microelectronics" and c == "CN" for n, c in inst_names(w)),
    "ASE": lambda w: any(n == "Advanced Semiconductor Engineering" for n, _ in inst_names(w)),
    "A*STAR IME(SG)": lambda w: any(n in ("Institute of Microelectronics", "Agency for Science, Technology and Research") and c == "SG" for n, c in inst_names(w)),
    "Samsung Electronics": lambda w: any(n in ("Samsung Electronics", "Samsung") for n, _ in inst_names(w)),
    "Fraunhofer IZM·TU Berlin": lambda w: any(n in ("Fraunhofer Institute for Reliability and Microintegration", "Technische Universität Berlin") for n, _ in inst_names(w)),
    "SIAT·SIAEM 선전(Rong Sun)": lambda w: any(n in ("Shenzhen Institutes of Advanced Technology", "Shenzhen Institute of Advanced Electronic Materials") for n, _ in inst_names(w)),
    "대만 학계(NCKU·NTHU·NYCU)": lambda w: any(n in ("National Cheng Kung University", "National Tsing Hua University", "National Yang Ming Chiao Tung University") for n, _ in inst_names(w)),
}
members = {g: [w["id"] for w in works if f(w)] for g, f in GROUPS.items()}

base = df[list(ISSUES)].mean()
summ, share, lift = [], {}, {}
for g, ids in members.items():
    sub = df.loc[ids]
    summ.append(dict(group=g, papers=len(sub), cites=int(sub.cites.sum()), ncites_sum=round(sub.ncites.sum(), 1),
                     ncites_mean=round(sub.ncites.mean(), 2), recent_23_26=int((sub.year >= 2023).sum())))
    share[g] = sub[list(ISSUES)].mean()
    lift[g] = share[g] / base
summ = pd.DataFrame(summ).sort_values("ncites_sum", ascending=False)
share = pd.DataFrame(share).T.loc[summ.group]; lift = pd.DataFrame(lift).T.loc[summ.group]
summ.to_csv(f"{OUT}/groups_summary.csv", index=False, encoding="utf-8-sig")
(share * 100).round(1).to_csv(f"{OUT}/group_issue_share_pct.csv", encoding="utf-8-sig")
lift.round(2).to_csv(f"{OUT}/group_issue_lift.csv", encoding="utf-8-sig")

# 그룹별 리포트: 특화 이슈(lift 상위, 비중 15% 이상) + 인용 상위 논문
lines = ["# 인용 상위 그룹별 주요 이슈", "",
         f"코퍼스: {len(df)}편 (배터리·비도메인·리뷰/서적 제외). 비중 = 그룹 논문 중 해당 이슈 언급 비율, lift = 비중 / 전체 평균.", ""]
for g in summ.group:
    s = summ.set_index("group").loc[g]
    lines.append(f"## {g}  (논문 {s.papers}, 인용 {s.cites}, 정규화인용합 {s.ncites_sum}, 최근 {s.recent_23_26})")
    top = pd.DataFrame({"share": share.loc[g], "lift": lift.loc[g]})
    top = top[top.share >= 0.15].sort_values("lift", ascending=False).head(6)
    lines.append("특화 이슈: " + ", ".join(f"{k} {v.share:.0%} (×{v.lift:.1f})" for k, v in top.iterrows()))
    for wid, r in df.loc[members[g]].sort_values("ncites", ascending=False).head(6).iterrows():
        lines.append(f"- ({r.year}, 인용 {r.cites}) {r.title}")
    lines.append("")
open(f"{OUT}/group_issues.md", "w", encoding="utf-8").write("\n".join(lines))
pd.set_option("display.width", 250)
print(summ.to_string(index=False)); print()
print((share * 100).round(0).astype(int).T.to_string()); print()
print("\n".join(lines))
