# 국회 의안 중국/외국 관련성 분석 도구

열린국회정보 OpenAPI(https://open.assembly.go.kr)에서 전체 의안을 수집하고,
제목/제안이유/주요내용/의안요약/발의자 전체를 대상으로 중국·외국 관련 키워드를
검색해 분류·통계·보고서를 생성하는 CLI 도구입니다.

## 왜 상세페이지를 별도로 스크레이핑하나요

의안 목록 OpenAPI(`ALLBILL` 등)는 의안번호·의안명·발의자·처리상태 등 메타데이터만
제공하고, **제안이유·주요내용·의안요약 원문은 필드로 내려주지 않습니다.** 이 정보는
목록 응답의 상세페이지 링크(`DETAIL_LINK`)가 가리키는 의안 상세 페이지 HTML에만
존재하므로, `detail_fetcher.py`가 해당 페이지를 받아 "제안이유"/"주요내용"/"의안요약"
섹션 헤더를 기준으로 본문을 잘라냅니다. 이 방식은 열린국회정보 API만으로는 불가능한
부분을 보완하기 위한 것이며, 사이트 HTML 구조가 바뀌면 파싱 결과가 비어있을 수 있습니다.

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # ASSEMBLY_API_KEY 채워넣기
export $(cat .env | xargs)
```

## 사용법

```bash
# 1) API 키/서비스ID/응답 필드명이 맞는지 먼저 확인 (1건만 조회)
python main.py probe

# 2) 전체 의안 수집 (기본: 22대 국회). 중간에 끊겨도 캐시(output/cache/)에서 이어서 진행됨
python main.py collect --age 22

# 소량으로 먼저 테스트하고 싶다면
python main.py collect --age 22 --limit 20

# 3) 보고서 생성 (①~⑥ 표 + 요약, output/report_age22.md)
python main.py report --age 22

# 한 번에
python main.py all --age 22
```

## 실제 API 스키마와 다를 경우

이 프로젝트는 네트워크가 차단된 환경에서 작성되어, 열린국회정보 OpenAPI의 정확한
서비스ID/응답 필드명을 실호출로 검증하지 못했습니다. `python main.py probe`로 실제
응답을 확인한 뒤, 다음 두 파일만 고치면 나머지 코드는 그대로 동작합니다.

- `law_bill_analysis/config.py`
  - `BILL_LIST_SERVICE_ID`: 의안 전체 목록 서비스 ID (기본 추정값 `ALLBILL`)
  - `FIELD_MAP`: 목록 응답의 실제 키 이름 매핑
  - `MEMBER_INFO_SERVICE_ID`, `MEMBER_FIELD_MAP`: 정당 정보 보강용 (기본 추정값 `ALLNAMEMBER`)
- `law_bill_analysis/detail_fetcher.py`
  - `_SECTION_HEADERS`: 상세페이지에서 제안이유/주요내용/의안요약을 찾는 헤더 키워드

## 분류 기준

- 중국 관련 키워드(중국, 중화인민공화국, 중국산, 대만, 홍콩, 마카오, 일대일로 등)가
  하나라도 매칭되면 `China`
- 중국 키워드 없이 외국 관련 키워드(외국, 해외, 국제, 수입, 수출, FTA, 국가안보 등)만
  매칭되면 `Foreign`
- 둘 다 없으면 미분류(보고서 목록에서 제외, 전체 건수 통계에는 포함)
- 순수 키워드 매칭이므로 "중국을 직접 대상으로 하는지"까지 완벽히 판별하지는
  못합니다. 애매한 건은 `matched_keywords` 필드로 어떤 키워드가 매칭됐는지 캐시에
  남겨두었으니, 정밀 검증이 필요하면 이 필드를 기준으로 사람이 재검토하세요.

## 출력

- `output/cache/bills_age{AGE}.jsonl`: 수집·분류된 원본 데이터 (재실행 시 캐시로 재사용)
- `output/cache/member_party.json`: 의원 이름 -> 정당 매핑 캐시
- `output/report_age{AGE}.md`: 의원 순위 / 정당별·연도별 통계 / 키워드 TOP20 /
  China·Foreign 법안 목록 / 요약이 담긴 마크다운 보고서

## 테스트

네트워크 호출 없이 검증 가능한 분류 로직과 통계 집계 로직에 대한 단위 테스트가
있습니다.

```bash
pytest tests/ -q
```
