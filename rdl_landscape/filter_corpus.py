#!/usr/bin/env python3
"""raw.jsonl 에서 배터리·비도메인 논문, 리뷰/서적류를 제외 → raw_filtered.jsonl + excluded.csv"""
import json, re, sys, csv

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/raw_filtered.jsonl"
EXC = sys.argv[3] if len(sys.argv) > 3 else "analysis/excluded.csv"

BATTERY = re.compile(r"lithium(?! niobate| tantalate)|batter|\bli[- ]?ion|li[- ]metal|dendrite|sodium[- ]ion|zinc[- ]ion|solid[- ]electrolyte", re.I)
PKG = re.compile(r"packag|interposer|wafer|\bdie\b|\bdies\b|chip|substrate|interconnect|fan-?out|\brdl|bump|tsv|semiconductor|solder|cowos|\binfo\b|flip", re.I)
# 패키징 단어가 없어도 RDL 공정/소재 논문이면 유지
PROCESS = re.compile(r"redistribution|dielectric|polyimide|plating|electroplat|leveler|photonic|lithograph|copper|\bcu\b|\bvias?\b|warpage|photosensitive|microstructure", re.I)
REVIEW_TITLE = re.compile(
    r"\breview\b|overview|recent advances|current advances|advances and (?:trends|challenges)|\btrends?\b|"
    r"perspective on|a perspective|challenges and prospects|roadmap|survey|tutorial|history of|outlook", re.I)
REVIEW_TYPES = {"review", "book", "book-chapter", "book-review", "editorial", "erratum", "report", "dataset"}

def text(w):
    inv = w.get("abstract_inverted_index") or {}
    kws = " ".join(k.get("display_name", "") for k in w.get("keywords") or [])
    topic = (w.get("primary_topic") or {}).get("display_name") or ""
    return " ".join([w.get("title") or "", " ".join(inv.keys()), kws, topic]), topic

kept = excl = 0
with open(RAW, encoding="utf-8") as f, open(OUT, "w", encoding="utf-8") as fo, \
     open(EXC, "w", newline="", encoding="utf-8-sig") as fe:
    wr = csv.writer(fe); wr.writerow(["reason", "year", "cited_by", "type", "title", "work_id"])
    for line in f:
        w = json.loads(line)
        title = w.get("title") or ""
        t, topic = text(w)
        reason = None
        if "Battery" in topic or BATTERY.search(title):
            reason = "battery"
        elif not PKG.search(t) and not PROCESS.search(title):
            reason = "off_domain"
        elif w.get("type") in REVIEW_TYPES or REVIEW_TITLE.search(title):
            reason = "review/book"
        if reason:
            excl += 1
            wr.writerow([reason, w.get("publication_year"), w.get("cited_by_count"), w.get("type"), title, w["id"]])
        else:
            kept += 1
            fo.write(line)
print(f"kept={kept} excluded={excl}")
