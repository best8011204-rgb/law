"""중앙 설정 모듈.

열린국회정보 OpenAPI(https://open.assembly.go.kr)의 정확한 요청/응답 필드명은
네트워크 접근 없이 이 세션에서 실검증하지 못했다. 아래 값들은 공개 문서에
근거한 최선의 추정치이며, 최초 실행 시 `python -m law_bill_analysis.cli probe`
로 실제 응답을 찍어보고 다르면 이 파일만 고치면 되도록 한 곳에 모아뒀다.
"""

import os

API_BASE_URL = "https://open.assembly.go.kr/portal/openapi"

# 의안 목록 서비스 ID. (전체 의안 목록 제공 서비스)
BILL_LIST_SERVICE_ID = os.environ.get("ASSEMBLY_BILL_SERVICE_ID", "ALLBILL")

API_KEY = os.environ.get("ASSEMBLY_API_KEY", "")

# 국회 대수. "all"이면 AGE 파라미터 없이 전체 대수를 조회한다(매우 오래 걸릴 수 있음).
DEFAULT_AGE = os.environ.get("ASSEMBLY_AGE", "22")

PAGE_SIZE = int(os.environ.get("ASSEMBLY_PAGE_SIZE", "100"))

REQUEST_TIMEOUT_SEC = 15
MAX_RETRIES = 4
RETRY_BACKOFF_BASE_SEC = 2
REQUEST_INTERVAL_SEC = float(os.environ.get("ASSEMBLY_REQUEST_INTERVAL_SEC", "0.2"))

# 목록 응답(row)에서 사용하는 필드명 매핑. 실제 API 응답 키가 다르면 여기만 수정.
FIELD_MAP = {
    "bill_id": "BILL_ID",
    "bill_no": "BILL_NO",
    "bill_name": "BILL_NAME",
    "propose_dt": "PROPOSE_DT",
    "proposer": "PROPOSER",  # 대표발의자 (콤마/기타 구분자로 공동발의자 포함되는 경우 있음)
    "publ_proposer": "PUBL_PROPOSER",  # 공동발의자 (있을 경우)
    "committee": "COMMITTEE",
    "proc_result": "PROC_RESULT",
    "detail_link": "DETAIL_LINK",
    "age": "AGE",
}

# 정당 정보는 ALLBILL 목록에 없는 경우가 많아, 국회의원 인적사항 API로 보강한다.
MEMBER_INFO_SERVICE_ID = os.environ.get("ASSEMBLY_MEMBER_SERVICE_ID", "ALLNAMEMBER")
MEMBER_FIELD_MAP = {
    "name": "HG_NM",
    "party": "POLY_NM",
}

CACHE_DIR = os.environ.get("ASSEMBLY_CACHE_DIR", "output/cache")
OUTPUT_DIR = os.environ.get("ASSEMBLY_OUTPUT_DIR", "output")

USER_AGENT = "law-bill-analysis/1.0 (+https://open.assembly.go.kr)"
