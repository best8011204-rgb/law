#!/usr/bin/env python3
"""
OpenAlex RDL(Redistribution Layer) 문헌 수집기
- 여러 검색어로 OpenAlex /works 를 커서 페이징 수집 → work ID 기준 중복 제거
- 출력: works.csv (논문 1행), authorships.csv (저자-소속 1행), raw.jsonl, summary.txt

사용:
  export OPENALEX_API_KEY=xxxx          # openalex.org/settings/api 에서 무료 발급
  pip install requests
  python openalex_rdl_collect.py --from 2018 --to 2026 --out data
"""
import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict

import requests

BASE = "https://api.openalex.org/works"

# 검색어: 필요 시 자유롭게 추가/삭제. 따옴표 = 구(phrase) 검색.
# 'RDL' 단독은 동음이의(다른 분야 약어)가 많아 제외하고 구 단위로 검색.
QUERIES = {
    "rdl": '"redistribution layer"',
    "rdl_interposer": '"RDL interposer"',
    "fowlp": '"fan-out wafer level"',
    "foplp": '"fan-out panel level"',
    "fanout_pkg": '"fan-out packaging"',
    "organic_interposer": '"organic interposer"',
    "fine_pitch_rdl": '"fine pitch" redistribution',
}

SELECT = ",".join([
    "id", "doi", "title", "publication_year", "type", "primary_location",
    "authorships", "abstract_inverted_index", "keywords", "primary_topic",
    "cited_by_count",
])

session = requests.Session()


def get(params):
    """429/5xx 지수 백오프 재시도."""
    for attempt in range(7):
        r = session.get(BASE, params=params, timeout=90)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            print(f"  ! HTTP {r.status_code}, {wait}s 후 재시도", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
    raise RuntimeError("재시도 한도 초과")


def build_params(query, y0, y1, api_key, mode):
    # API 키는 URL 파라미터 대신 Authorization 헤더로 전송 (main()에서 session에 설정)
    p = {"select": SELECT, "per_page": 200, "cursor": "*"}
    year_f = f"publication_year:{y0}-{y1}"
    if mode == "title_abstract":
        # 제목+초록에서만 검색 (전문 검색 노이즈 배제)
        p["filter"] = f"title_and_abstract.search:{query},{year_f}"
    else:
        # fallback: search 파라미터 (제목/초록/전문)
        p["filter"] = year_f
        p["search"] = query
    return p


def fetch_query(name, query, y0, y1, api_key, max_n):
    mode = "title_abstract"
    params = build_params(query, y0, y1, api_key, mode)
    try:
        data = get(params)
    except RuntimeError as e:
        if "400" in str(e):
            print(f"  ! title_and_abstract 필터 거부 → search 모드로 전환 ({name})",
                  file=sys.stderr)
            mode = "search"
            params = build_params(query, y0, y1, api_key, mode)
            data = get(params)
        else:
            raise
    total = data["meta"].get("count")
    print(f"[{name}] {query}  mode={mode}  count={total}")
    out = []
    while True:
        out.extend(data["results"])
        if max_n and len(out) >= max_n:
            out = out[:max_n]
            break
        nxt = data["meta"].get("next_cursor")
        if not nxt or not data["results"]:
            break
        params["cursor"] = nxt
        time.sleep(0.12)  # 초당 ~8건 이하로 유지
        data = get(params)
        print(f"  ... {len(out)}/{total}", end="\r")
    print(f"  수집 {len(out)}건            ")
    return out, mode, total


def rebuild_abstract(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="y0", type=int, default=2018)
    ap.add_argument("--to", dest="y1", type=int, default=2026)
    ap.add_argument("--out", default="data")
    ap.add_argument("--max-per-query", type=int, default=0, help="0=무제한(테스트 시 50 권장)")
    args = ap.parse_args()

    api_key = os.environ.get("OPENALEX_API_KEY")
    if not api_key:
        sys.exit("OPENALEX_API_KEY 환경변수가 없습니다. openalex.org/settings/api 에서 발급하세요.")
    session.headers["Authorization"] = f"Bearer {api_key}"
    os.makedirs(args.out, exist_ok=True)

    works = {}
    matched = defaultdict(set)
    qlog = []
    for name, q in QUERIES.items():
        res, mode, total = fetch_query(name, q, args.y0, args.y1, api_key, args.max_per_query)
        qlog.append((name, q, mode, total, len(res)))
        for w in res:
            works[w["id"]] = w
            matched[w["id"]].add(name)

    # raw 보존
    with open(os.path.join(args.out, "raw.jsonl"), "w", encoding="utf-8") as f:
        for w in works.values():
            f.write(json.dumps(w, ensure_ascii=False) + "\n")

    wrows, arows = [], []
    for wid, w in works.items():
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        inst_types, countries = set(), set()
        for a in w.get("authorships") or []:
            insts = a.get("institutions") or [{}]
            for inst in insts:
                t = inst.get("type") or ""
                c = inst.get("country_code") or ""
                if t:
                    inst_types.add(t)
                if c:
                    countries.add(c)
                arows.append({
                    "work_id": wid,
                    "year": w.get("publication_year"),
                    "author_position": a.get("author_position"),
                    "author": (a.get("author") or {}).get("display_name"),
                    "institution_id": inst.get("id"),
                    "institution": inst.get("display_name"),
                    "institution_type": t,
                    "country": c,
                })
        abstract = rebuild_abstract(w.get("abstract_inverted_index"))
        wrows.append({
            "work_id": wid,
            "doi": w.get("doi"),
            "title": w.get("title"),
            "year": w.get("publication_year"),
            "type": w.get("type"),
            "venue": src.get("display_name"),
            "cited_by": w.get("cited_by_count"),
            "has_abstract": int(bool(abstract)),
            "abstract": abstract,
            "keywords": "; ".join(k.get("display_name", "") for k in (w.get("keywords") or [])),
            "primary_topic": (w.get("primary_topic") or {}).get("display_name"),
            "inst_types": "; ".join(sorted(inst_types)),
            "has_company": int("company" in inst_types),
            "countries": "; ".join(sorted(countries)),
            "matched_queries": "; ".join(sorted(matched[wid])),
        })

    def dump(path, rows):
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)

    dump(os.path.join(args.out, "works.csv"), wrows)
    dump(os.path.join(args.out, "authorships.csv"), arows)

    # 품질 점검 요약
    n = len(wrows)
    by_year = defaultdict(lambda: [0, 0, 0])  # total, abstract, company
    for r in wrows:
        y = r["year"]
        by_year[y][0] += 1
        by_year[y][1] += r["has_abstract"]
        by_year[y][2] += r["has_company"]
    venues = Counter(r["venue"] for r in wrows if r["venue"])

    lines = [f"고유 논문 수: {n}", "", "검색어별:"]
    for name, q, mode, total, got in qlog:
        lines.append(f"  {name:20s} {q:32s} mode={mode:14s} OpenAlex count={total}  수집={got}")
    lines += ["", "연도별 (총계 / 초록 보유율 / 기업 저자 포함 비율):"]
    for y in sorted(k for k in by_year if k):
        t, a, c = by_year[y]
        lines.append(f"  {y}: {t:5d}  abstract {a/t:5.1%}  company {c/t:5.1%}")
    lines += ["", "상위 게재지 20:"]
    lines += [f"  {cnt:5d}  {v}" for v, cnt in venues.most_common(20)]
    ectc = sum(cnt for v, cnt in venues.items() if "Electronic Components and Technology" in v)
    lines += ["", f"ECTC 계열 게재지 논문 수: {ectc}"]
    summary = "\n".join(lines)
    with open(os.path.join(args.out, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    print("\n" + summary)


if __name__ == "__main__":
    main()
