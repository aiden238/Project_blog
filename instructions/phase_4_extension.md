# Phase 4 — Extension

## Context

Phase 4는 Tistory export 어댑터, pgvector 유사도 검색, LiteLLM 옵션 경로, S3 미러를 선택적으로 추가한다. 각 기능은 독립 feature flag로 on/off 가능하며 기본값은 off. Phase 3 안정화 완료가 선행 조건이다.

## Harness / Environment

### G-H1. Tistory Adapter

Tistory OpenAPI로 게시한다. 앱 등록·토큰 발급은 사용자가 수행하고 `.env`의 `TISTORY_ACCESS_TOKEN`에 주입. 어댑터는 `src/publish/tistory.py`에 두고 Outbox `target='tistory'` 이벤트만 처리한다.

- [ ] 앱 등록·토큰 발급 run-book
- [ ] publish 어댑터 스모크 테스트
- [ ] 실패 시 dead 격리 확인
- [ ] 토큰 만료 감지 로그

### G-H2. pgvector 임베딩 인덱스

`items.embedding vector(768)` 컬럼과 ivfflat 인덱스를 추가한다. 임베딩은 sentence-transformers `intfloat/multilingual-e5-base`로 산출. GPU 가용 시 CUDA, 미가용 시 CPU 폴백. 배치 크기는 `.env`로 주입.

- [ ] 컬럼·인덱스 마이그레이션
- [ ] 임베딩 워커 구현
- [ ] CPU 폴백 경로 테스트
- [ ] 검색 레이턴시 측정

## Meta

### G-M1. 게시 메타데이터

Tistory 게시 건은 `items.meta`에 `published_url, published_at, tistory_post_id, tistory_category`를 기록한다. 재게시는 Tistory 업데이트 API로만 수행하며 신규 레코드 생성은 금지한다.

- [ ] meta 필드 스키마 확정
- [ ] 업데이트 경로 통합 테스트
- [ ] 신규 생성 차단 테스트

### G-M2. 유사도 기반 중복 제거

Phase 1의 SimHash에 더해 임베딩 코사인 유사도 0.92 이상을 3차 중복 판정 기준으로 추가한다. 적용 전 최근 30일 데이터로 backfill을 실행하고 false positive 수동 검토를 거친다.

- [ ] 코사인 임계값 상수화
- [ ] backfill 스크립트 작성
- [ ] false positive 리뷰 로그

## Eval / Observability

### G-E1. 게시 성공률

Tistory 게시 시도·성공·실패를 `metrics`에 `kind='publish'`로 기록한다. 7일 평균 성공률이 80% 미만으로 떨어지면 자동 게시 게이트를 강제 off하고 사용자에게 `logs/alerts.log`로 통지한다.

- [ ] 성공률 산출 스크립트
- [ ] 강제 off 동작 확인
- [ ] 복구 절차 문서화

### G-E2. 임베딩 품질 샘플링

주 1회 무작위 20건의 임베딩 기반 유사 쿼리 결과를 샘플링해 `logs/embedding_sample/`에 저장한다. 사람이 주관 적합도를 기록하고 7일 평균 적합도 0.7 미만이면 모델 재검토 항목으로 자동 등록한다.

- [ ] 샘플링 스크립트 구현
- [ ] 사람 평가 기록 양식
- [ ] 재검토 자동 트리거

## Protocol

### G-P1. 4중 AND 자동 게시 게이트

`track=A ∧ license_class=first_party ∧ auto_publish_allowed=true ∧ score≥AUTO_PUBLISH_THRESHOLD`가 모두 참일 때만 Tistory 전송이 큐잉된다. 하나라도 거짓이면 Notion projection까지만 수행한다.

- [ ] 게이트 함수 단위 테스트
- [ ] 분기별 로그 INFO 레벨
- [ ] 거부 사유 로그 기록

### G-P2. auto_publish_allowed 조정

사용자가 `sources/<id>.yaml`의 `auto_publish_allowed`를 수정하고 `pipeline sources sync`를 실행하면 반영된다. 초기값은 모두 false. 전환 이력은 `logs/auto_publish_changes.log`에 append한다.

- [ ] sync 후 반영 통합 테스트
- [ ] 변경 이력 로그 포맷
- [ ] 반영 확인 커맨드 제공

## Governance

### G-G1. 자동 게시 권한

`auto_publish_allowed=true` 전환은 사용자 승인 이벤트다. 에이전트는 제안만 수행하고 직접 true로 변경하지 않는다. 위반 발견 시 즉시 false로 롤백하고 사용자에게 `error_log.md` 기록을 요청한다.

- [ ] 에이전트 직접 변경 차단 lint
- [ ] 롤백 절차 자동화
- [ ] 위반 감지 테스트

### G-G2. 상용 경로(LiteLLM) 활성화 조건

LiteLLM 어댑터는 `.env`의 `USE_COMMERCIAL_LLM=1`과 사용자 승인 없이 활성화할 수 없다. 활성화돼도 기본 경로는 Ollama이며 비용 초과 감시 알림은 `logs/cost.log`에 누적된다.

- [ ] 플래그 게이팅 테스트
- [ ] 비용 로그 포맷 정의
- [ ] 승인 이력 보관 경로

### G-G3. Phase 4 기능 토글

Tistory·pgvector·LiteLLM·S3 미러는 각각 독립 feature flag로 제어한다. 전역 on/off 단일 스위치는 두지 않으며 한 기능 실패가 다른 기능으로 전파되지 않는 격리 구조를 유지한다.

- [ ] 기능별 flag `.env` 키 정의
- [ ] 격리 통합 테스트
- [ ] 장애 전파 차단 검증

## 변경 기록

- 2026-04-20 초안 작성.
