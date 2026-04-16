# Phase 2 — LLM & Notion

## Context

Phase 2는 LLM(요약·태그·초안·클러스터 설명)과 Outbox 기반 Notion projection을 구현한다. 기본 경로는 Ollama + Gemma 3 12B 로컬 추론. 상용 API는 옵션 어댑터로만 유지하며 기본 경로에서 호출되지 않는다.

## Harness / Environment

### G-H1. Ollama 어댑터

`src/llm/ollama_client.py`가 HTTP로 Ollama에 접근한다. 모델·온도·max_tokens는 `.env`로 주입. 호출 실패는 3회 재시도 후 `items.status='llm_failed'`로 격리하고 파이프라인은 다음 아이템으로 계속 진행한다.

- [ ] ollama_client 구현
- [ ] 타임아웃·재시도 상수 주입
- [ ] 실패 격리 경로 테스트
- [ ] 배치 호출 제한 상수화

### G-H2. Outbox 워커

`src/workers/outbox_dispatcher.py`가 `SELECT ... FOR UPDATE SKIP LOCKED`로 큐를 처리한다. 성공 시 status='sent', 5회 실패 시 'dead', 그 외 retry_count만 증가. 워커는 별도 프로세스로 분리 운영한다.

- [ ] SKIP LOCKED 쿼리 작성
- [ ] 재시도 상한 5회 테스트
- [ ] dead 상태 알림 연동
- [ ] 별도 프로세스 실행 스크립트

## Meta

### G-M1. 프롬프트 템플릿 버전

요약·태그·초안·클러스터 설명 프롬프트는 `src/prompts/<task>_v<N>.txt`로 버전 관리한다. 사용 버전 ID는 `items.meta.prompt_version`에 기록해 재현성을 확보하고 A/B 비교를 가능하게 한다.

- [ ] 프롬프트 버전 네이밍 규약
- [ ] meta.prompt_version 기록
- [ ] 버전 diff 로그
- [ ] 구버전 보존 정책

### G-M2. 통합 Notion DB 스키마

통합 DB 단일 구성 + 필터 뷰로 운영한다. 속성은 `title, source_id, track, status, score, tags, license_class, localfs_path, draft_url`. 필터 뷰는 "Track A 초안", "Track B 인사이트", "DLQ" 3개를 기본으로 고정한다.

- [ ] Notion DB 단일 생성
- [ ] 필터 뷰 3종 정의
- [ ] 속성 타입 코드 선언

## Eval / Observability

### G-E1. 초안 품질 기록

생성 초안은 길이·코드블록 수·제목 적합도·요약 압축률을 계산해 `metrics`에 `kind='draft'`로 저장한다. 점수 하위 10%는 주간 리뷰 큐 자동 추가. 분포는 주간 리포트에 포함한다.

- [ ] 점수 산출 함수
- [ ] 하위 10% 리뷰 큐 테이블
- [ ] 주간 분포 리포트

### G-E2. LLM 처리량 관측

Ollama 호출의 prompt_tokens·completion_tokens·wall_time을 `metrics`에 `kind='llm'`으로 기록한다. 일일 평균 throughput과 p95 latency를 리포트에 포함해 Gemma 12B 구동 적정성을 상시 모니터링한다.

- [ ] 토큰·시간 기록 미들웨어
- [ ] p95 집계 쿼리
- [ ] 모델 강등 트리거 기준

## Protocol

### G-P1. Notion 페이지 생성 규칙

Notion 페이지 본문에는 요약 250자 + LocalFS 경로 링크만 저장한다. 초안 원문·raw·정제 텍스트는 본문 블록에 넣지 않는다. 속성 필드 직접 편집은 projection 갱신과 충돌하지 않는 필드 한정.

- [ ] 본문 길이 초과 차단 테스트
- [ ] localfs_path 링크 유효성
- [ ] 속성 필드 편집 가이드 문서화

### G-P2. Outbox 재시도 백오프

재시도 간격은 `1m → 5m → 15m → 1h → 6h` 지수 백오프. 5회 초과 시 dead 이동. dead는 수동 커맨드 `pipeline outbox replay <id>`로만 복구하며 자동 replay는 금지한다.

- [ ] 백오프 스케줄 구현
- [ ] replay 커맨드 구현
- [ ] 자동 replay 차단 테스트

## Governance

### G-G1. Notion 본문 저장 금지

초안·정제 텍스트·raw 원본을 Notion 블록 본문에 저장하지 않는다. Notion은 projection 한정이며 SoT가 아니다. 위반 발견 시 즉시 마이그레이션해 LocalFS로 이전하고 `error_log.md`에 사용자가 직접 기록한다.

- [ ] 본문 용량 lint (250자 초과 차단)
- [ ] 위반 마이그레이션 스크립트
- [ ] error_log 기록 플로우 안내

### G-G2. 상용 API 사용 승인

상용 LLM API 호출은 `.env`의 `USE_COMMERCIAL_LLM=1` 플래그와 사용자 승인 없이는 활성화 금지. 기본 경로는 항상 Ollama. 어댑터가 활성화돼도 Ollama 실패 시 자동 폴백은 하지 않는다.

- [ ] 플래그 게이팅 테스트
- [ ] 자동 폴백 차단 확인
- [ ] 비용 로그 누적 경로

## 변경 기록

- 2026-04-20 초안 작성.
