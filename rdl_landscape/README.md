# RDL 문헌 수집 (OpenAlex) — Claude Code 실행 가이드

## 0. 준비
1. OpenAlex 무료 API 키 발급: https://openalex.org/settings/api
2. 작업 폴더 생성 (예: `rdl_landscape/`) 후 `openalex_rdl_collect.py`, 이 README를 넣기
3. API 키를 환경변수로 등록 (키를 채팅창에 붙여넣지 않는 것을 권장)
   - macOS/Linux: `~/.zshrc` 등에 `export OPENALEX_API_KEY=발급키`
   - Windows: `setx OPENALEX_API_KEY "발급키"`
   - 등록 후 Claude Code 앱 재시작
4. 회사망 프록시 환경이면 `HTTPS_PROXY` 가 설정돼 있어야 함 (requests가 자동 사용)

## 1. Claude Code에 붙여넣을 지시문

```
이 폴더의 openalex_rdl_collect.py로 OpenAlex에서 RDL 관련 논문을 수집해줘.

1) pip install requests (가상환경 있으면 그 안에서)
2) 테스트: python openalex_rdl_collect.py --from 2018 --to 2026 --out data_test --max-per-query 50
   - 에러 나면 원인 보고 후 수정. 'title_and_abstract 필터 거부' 경고가 나오면 그대로 진행해도 됨.
3) data_test/summary.txt 를 보여주고, works.csv에서 무작위 15건 제목을 뽑아
   RDL/패키징과 무관한 노이즈 비율을 대략 판정해줘.
4) 노이즈가 30% 넘으면 해당 검색어(matched_queries 기준)를 알려주고 멈춰. 아니면 본 수집:
   python openalex_rdl_collect.py --from 2018 --to 2026 --out data
5) data/summary.txt 를 보여줘. 특히 연도별 초록 보유율과 ECTC 계열 논문 수.
```

## 2. 결과물
| 파일 | 내용 |
|---|---|
| `data/works.csv` | 논문 1행: 제목, 연도, 게재지, 초록, 키워드, 소속 유형, 기업 저자 포함 여부, 매칭 검색어 |
| `data/authorships.csv` | 저자–소속 1행: 기관명, 기관 유형(education/company/facility…), 국가 |
| `data/raw.jsonl` | OpenAlex 원본 응답 (재분석용) |
| `data/summary.txt` | 품질 점검 요약 |

→ `works.csv`, `authorships.csv`, `summary.txt` 세 개를 Claude 채팅에 첨부하면 이후 분석(도메인 사전 태깅, 시계열, 소속 구성 변화, 클러스터링) 진행.

## 3. 점검 포인트
- **초록 보유율**: IEEE 학회 논문은 초록이 비어 있을 수 있음. 낮으면 IEEE Xplore export로 보완.
- **검색어 노이즈**: `matched_queries` 컬럼으로 검색어별 품질 확인. 검색어는 스크립트 상단 `QUERIES`에서 수정.
- **최근 연도 과소 집계**: 2026년은 색인 지연으로 적게 잡힘. 추세 해석 시 별도 표시.
