# Tech Stack

## Context

프로젝트는 무료·최소 종속·로컬 우선을 전제한다. 상용 API와 외부 SaaS는 옵션 어댑터로만 두며 기본 경로에서 제외한다. 라이선스는 MIT/Apache-2.0/BSD 계열만 기본 허용한다.

## Harness / Environment

### G-H1. 언어 및 패키지 관리

Python 3.11+를 고정한다. 의존성은 `pyproject.toml`로 선언하고 `uv`로 해석·잠금한다. 가상환경 경로는 `.venv/`로 고정, 실행은 `uv run` 경유로 통일해 인터프리터 드리프트를 차단한다.

- [ ] Python 3.11+ 설치 확인
- [ ] uv 설치 및 버전 기록
- [ ] `.venv/` 생성과 `uv.lock` 커밋
- [ ] `uv run` 외 직접 python 호출 금지 규약 합의

### G-H2. DB 인프라

Postgres 15 + pgvector 확장을 `docker/compose.yml`로 기동한다. 접속은 `.env`의 `DATABASE_URL`로만 주입하고 코드 하드코딩은 금지. 로컬·CI 버전 동일 유지, 임의 메이저 업그레이드 금지.

- [ ] docker-compose up 성공
- [ ] `CREATE EXTENSION vector` 확인
- [ ] DATABASE_URL 주입 경로 일원화
- [ ] 하드코딩 접속 문자열 lint 추가

### G-H3. 로컬 LLM 런타임

Ollama + Gemma 3 12B를 RTX 5070 Ti(16GB VRAM) 기준 Q4_K_M으로 구동한다. 첫 실행에서 VRAM 사용량을 측정하고 12GB 초과 시 Q4_0로 강등, 14GB 초과 시 7B 모델로 교체한다.

- [ ] Ollama 설치
- [ ] `gemma3:12b` Q4_K_M 태그 pull
- [ ] `nvidia-smi` VRAM 사용량 로그 저장
- [ ] 한국어 기술글 smoke prompt 통과 확인

## Meta

### G-M1. 라이선스 화이트리스트

MIT·Apache-2.0·BSD만 기본 허용한다. LGPL은 동적 링크 전제에서만 허용, GPL·AGPL은 전면 금지. 신규 의존성 추가 시 `docs/license_audit.md`에 라이선스·버전·용도를 함께 기록한다.

- [ ] license_audit.md 초기 작성
- [ ] GPL/AGPL 검출 pre-commit hook
- [ ] PR 템플릿에 라이선스 란 추가

### G-M2. 배제 목록

LangChain·MinIO(AGPL)·newspaper3k·Airflow/Prefect/Dagster는 초기 스택에서 배제한다. 필요 기능은 직접 조립 또는 경량 대안(APScheduler·trafilatura 등)으로 대체한다.

- [ ] import lint 규칙에 배제 목록 반영
- [ ] pre-commit에서 차단 동작 확인
- [ ] 배제 목록 우회 요청은 문서 개정 PR 선행

## Eval / Observability

### G-E1. 런타임 버전 로깅

앱 기동 시 Python·Postgres·Ollama·주요 라이브러리 버전을 `logs/boot.json`에 기록한다. 버전 mismatch는 경고 로그를 남기되 기동 자체는 차단하지 않는다.

- [ ] boot.json 생성 루틴
- [ ] 기대 버전 상수 정의
- [ ] mismatch 경고 로그 포맷 확정

## Protocol

### G-P1. 의존성 업그레이드 절차

마이너·패치는 PR 단위 허용, 메이저는 별도 이슈와 회귀 테스트 후 진행한다. 업그레이드 PR에는 Phase 1 스모크 스크립트 통과 로그를 첨부하고 실패 시 머지 차단한다.

- [ ] PR 템플릿에 스모크 로그 란
- [ ] 메이저 업그레이드 이슈 템플릿
- [ ] 회귀 테스트 목록 정의

## Governance

### G-G1. 스택 변경 권한

본 문서에 기재되지 않은 신규 스택 도입은 라우터(CLAUDE.md) 업데이트와 본 문서 개정을 동반해야 한다. 문서 업데이트 없는 import는 lint 단계에서 차단된다.

- [ ] 스택 추가 시 tech_stack.md 개정
- [ ] CLAUDE.md 라우팅 동기 업데이트
- [ ] import 화이트리스트 유지

## 변경 기록

- 2026-04-20 초안 작성. Gemma 3 12B + RTX 5070 Ti 기준 반영.
