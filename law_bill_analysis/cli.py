"""CLI 진입점.

사용법:
  python main.py probe                     # API 연결/응답 스키마 확인 (1건만 조회)
  python main.py collect --age 22          # 전체 의안 수집 + 상세조회 + 분류 (캐시에 저장)
  python main.py report --age 22           # 캐시된 데이터로 마크다운 보고서 생성
  python main.py all --age 22              # collect + report 한 번에
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import config
from .api_client import AssemblyApiClient, AssemblyApiError
from .collect import collect_bills
from .report import generate_report


def cmd_probe(args: argparse.Namespace) -> int:
    """API 키/서비스ID가 유효한지, 응답 필드명이 config.FIELD_MAP과 일치하는지 확인한다."""
    params = {"pIndex": 1, "pSize": 1}
    if args.age and args.age.lower() != "all":
        params[config.FIELD_MAP["age"]] = args.age

    try:
        client = AssemblyApiClient()
        payload = client._get(config.BILL_LIST_SERVICE_ID, params)
    except AssemblyApiError as exc:
        print(f"API 호출 실패: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(
        "\n위 응답의 row 안에 있는 실제 키 이름이 law_bill_analysis/config.py의 "
        "FIELD_MAP 값과 다르면 그 파일을 수정하세요.",
        file=sys.stderr,
    )

    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "probe_response.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    bills = collect_bills(
        age=args.age,
        fetch_details=not args.no_details,
        limit=args.limit,
        resume=not args.no_resume,
    )
    print(f"수집 완료: {len(bills)}건 (캐시: output/cache/bills_age{args.age}.jsonl)")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .collect import _cache_path, _load_cache

    cache_path = _cache_path(args.age)
    if not cache_path.exists():
        print(f"캐시 파일이 없습니다: {cache_path}. 먼저 collect를 실행하세요.", file=sys.stderr)
        return 1

    bills = list(_load_cache(cache_path).values())
    report_text = generate_report(bills)

    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"report_age{args.age}.md"
    out_path.write_text(report_text, encoding="utf-8")

    print(f"보고서 생성 완료: {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="국회 의안 중국/외국 관련성 분석 도구")
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe", help="API 연결 및 응답 스키마 확인")
    p_probe.add_argument("--age", default=config.DEFAULT_AGE, help="국회 대수 (예: 22, 'all')")
    p_probe.set_defaults(func=cmd_probe)

    p_collect = sub.add_parser("collect", help="전체 의안 수집 + 상세조회 + 분류")
    p_collect.add_argument("--age", default=config.DEFAULT_AGE, help="국회 대수 (예: 22, 'all')")
    p_collect.add_argument("--no-details", action="store_true", help="상세페이지 스크레이핑 생략(목록 필드만 분류)")
    p_collect.add_argument("--limit", type=int, default=None, help="테스트용 최대 건수 제한")
    p_collect.add_argument("--no-resume", action="store_true", help="캐시 무시하고 처음부터 재수집")
    p_collect.set_defaults(func=cmd_collect)

    p_report = sub.add_parser("report", help="캐시된 데이터로 보고서 생성")
    p_report.add_argument("--age", default=config.DEFAULT_AGE)
    p_report.set_defaults(func=cmd_report)

    p_all = sub.add_parser("all", help="collect + report")

    def cmd_all(args: argparse.Namespace) -> int:
        rc = cmd_collect(args)
        if rc != 0:
            return rc
        return cmd_report(args)

    p_all.add_argument("--age", default=config.DEFAULT_AGE)
    p_all.add_argument("--no-details", action="store_true")
    p_all.add_argument("--limit", type=int, default=None)
    p_all.add_argument("--no-resume", action="store_true")
    p_all.set_defaults(func=cmd_all)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
