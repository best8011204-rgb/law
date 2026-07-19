"""중앙 설정 모듈.

BILL_LIST_SERVICE_ID와 FIELD_MAP은 2026-07-19 GitHub Actions에서 실제
ASSEMBLY_API_KEY로 검증했다 (scripts/probe_candidates.py 실행 결과).
"ALLBILL"은 존재하지 않는 서비스ID였고, 실제로는 "TVBPMBILL11"이 의안 목록을
반환한다.
"""

import os

API_BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# 의안 목록 서비스 ID. (전체 의안 목록 제공 서비스)
BILL_LIST_SERVICE_ID = os.environ.get("ASSEMBLY_BILL_SERVICE_ID", "TVBPMBILL11")

API_KEY = os.environ.get("ASSEMBLY_API_KEY", "")

# 국회 대수. "all"이면 AGE 파라미터 없이 전체 대수를 조회한다(매우 오래 걸릴 수 있음).
DEFAULT_AGE = os.environ.get("ASSEMBLY_AGE", "22")

PAGE_SIZE = int(os.environ.get("ASSEMBLY_PAGE_SIZE", "100"))

REQUEST_TIMEOUT_SEC = 15
MAX_RETRIES = 4
RETRY_BACKOFF_BASE_SEC = 2
REQUEST_INTERVAL_SEC = float(os.environ.get("ASSEMBLY_REQUEST_INTERVAL_SEC", "0.2"))

# 목록 응답(row)에서 사용하는 필드명 매핑 (TVBPMBILL11 실제 응답 기준으로 검증됨).
FIELD_MAP = {
    "bill_id": "BILL_ID",
    "bill_no": "BILL_NO",
    "bill_name": "BILL_NAME",
    "propose_dt": "PROPOSE_DT",
    "proposer": "PROPOSER",  # 대표발의자 표시용 텍스트, 예: "강승규의원 등 11인"
    "rst_proposer": "RST_PROPOSER",  # 대표발의자 이름만 (예: "강승규")
    "publ_proposer": "PUBL_PROPOSER",  # TVBPMBILL11 응답에는 공동발의자 필드가 없어 항상 빈 값
    "committee": "CURR_COMMITTEE",
    "proc_result": "PASS_GUBUN",
    "detail_link": "LINK_URL",
    "age": "AGE",
}

# 정당 정보는 TVBPMBILL11 목록에 없어 국회의원 인적사항 API로 보강한다.
# MEMBER_INFO_SERVICE_ID는 아직 실검증하지 못한 추정값이며, 필요 시 이 값도 확인 필요.
MEMBER_INFO_SERVICE_ID = os.environ.get("ASSEMBLY_MEMBER_SERVICE_ID", "ALLNAMEMBER")
MEMBER_FIELD_MAP = {
    "name": "HG_NM",
    "party": "POLY_NM",
}

CACHE_DIR = os.environ.get("ASSEMBLY_CACHE_DIR", "output/cache")
OUTPUT_DIR = os.environ.get("ASSEMBLY_OUTPUT_DIR", "output")

USER_AGENT = "law-bill-analysis/1.0 (+https://open.assembly.go.kr)"
