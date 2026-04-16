# Phase 0 — Foundation

## Context

Phase 0은 Postgres 스키마·Alembic·Source Registry·LocalFS 스캐폴드·설정 로더를 구축한다. 완료 조건은 `python -m pipeline sources list`가 3개 이상 출처를 반환하는 것. 파이프라인 로직 구현은 Phase 1 몫이다.

## Harness / Environment

### G-H1. Alembic 초기화

`db/migrations/`에 Alembic을 초기화한다. `alembic.ini`의 `sqlalchemy.url`은 env에서 읽도록 치환. 첫 revision에 `sources`, `items`, `outbox`, `metrics` 4개 테이블을 함께 포함한다.

- [ ] `alembic init` 완료
- [ ] url env 치환 확인
- [ ] 4개 테이블 초기 revision
- [ ] `alembic upgrade head` 성공

### G-H2. 설정 로더

`src/config.py`에서 pydantic-settings로 `.env`를 로드한다. 모든 상수는 이 모듈을 경유한다. 직접 `os.environ` 접근은 lint로 차단하고 `.env.example` 템플릿을 함께 제공한다.

- [ ] Settings 클래스 정의
- [ ] `os.environ` 직접 접근 금지 lint
- [ ] `.env.example` 템플릿 제공
- [ ] 필수 키 누락 시 기동 실패

## Meta

### G-M1. Source YAML 스키마

`sources/<id>.yaml`은 `id, track, kind, endpoint, license_class, trust, auto_publish_allowed, language, topics, fetch, extract, dedupe, post_rules, enabled` 필드를 포함한다. 미정의 필드는 로드 실패.

- [ ] jsonschema 검증기 작성
- [ ] 기본 3개 출처 YAML 작성
- [ ] 필드 누락 오류 테스트
- [ ] 초기 `auto_publish_allowed: false` 고정

### G-M2. Postgres 핵심 스키마

`sources`는 YAML 런타임 캐시, `items`는 수집 아이템, `outbox`는 비동기 이벤트 큐, `metrics`는 관측·평가 지표. 각 테이블 PK·인덱스는 초기 revision에서 확정한다.

- [ ] 4개 테이블 컬럼 확정
- [ ] canonical_url UNIQUE 제약
- [ ] (outbox.status) 인덱스
- [ ] (metrics.kind, recorded_at) 인덱스

## Eval / Observability

### G-E1. 마이그레이션 검증

각 revision 적용 후 `alembic check`과 `scripts/verify_schema.py`로 검증한다. 실패 시 즉시 rollback하고 로그를 `logs/alembic/`에 보존한다. 성공 로그도 같은 경로에 append한다.

- [ ] verify_schema.py 작성
- [ ] rollback run-book 문서화
- [ ] 로그 경로·포맷 확정

## Protocol

### G-P1. YAML → Postgres sync

`python -m pipeline sources sync`가 YAML을 읽어 Postgres에 upsert한다. YAML이 SoT이므로 반대 방향 sync는 금지한다. Postgres에만 존재하는 레코드는 `enabled=false`로 soft disable 처리.

- [ ] sync 커맨드 구현
- [ ] 반대 방향 sync 차단 테스트
- [ ] soft disable 동작 확인
- [ ] dry-run 옵션 제공

## Governance

### G-G1. 스키마 변경 권한

Postgres 스키마 변경은 Alembic revision을 통해서만 수행한다. `DROP` 계열은 별도 승인 PR 필요. 프로덕션 데이터가 있는 테이블의 컬럼 삭제 전 30일 deprecation 로그를 필수로 남긴다.

- [ ] Alembic 외 DDL 금지 lint
- [ ] DROP PR 체크리스트
- [ ] deprecation 로그 양식 정의

### G-G2. 초기 출처 정책

Phase 0에서는 1차 출처(공식 블로그·릴리즈) 3개만 등록한다. 2차 출처·커뮤니티·유료 자료는 Phase 1 이후 추가한다. 초기 모든 출처의 `auto_publish_allowed`는 false로 시작한다.

- [ ] 1차 출처 3개 YAML 작성
- [ ] 2차 출처 추가 차단 규약
- [ ] auto_publish_allowed 일괄 false 검증

## 변경 기록

- 2026-04-20 초안 작성.
