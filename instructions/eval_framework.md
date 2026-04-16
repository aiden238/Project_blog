# Evaluation Framework

## Context

평가는 파이프라인 품질 게이트와 운영 관측을 동시에 제공한다. 품질 점수는 자동 게시 게이트에, 관측 지표는 스케줄러·알림에 사용된다. 모든 지표는 Postgres `metrics`에 단일 스키마로 기록한다.

## Harness / Environment

### G-H1. 지표 저장소

평가 지표는 `metrics(id, kind, target_id, value, meta JSONB, recorded_at)` 단일 테이블에 기록한다. 외부 시계열 DB 도입 금지. 조회는 SQL 뷰와 `scripts/report_daily.py`로만 수행한다.

- [ ] metrics 테이블 Alembic revision
- [ ] (kind, recorded_at) 인덱스
- [ ] 외부 TSDB 배제 lint

## Meta

### G-M1. 품질 점수 정의

item 점수는 `0.3·length_norm + 0.3·structure + 0.2·source_trust + 0.2·novelty`로 산출한다. 각 항목은 0~1 정규화. 정의 변경 시 이전 점수 재계산 배치를 반드시 함께 실행한다.

- [ ] 점수 계산 함수 구현
- [ ] 각 항목별 단위 테스트
- [ ] 재계산 배치 스크립트

### G-M2. 관측 지표 목록

`fetch_success_rate`, `extract_failure_rate`, `dedupe_hit_rate`, `draft_latency_p95`, `outbox_lag`, `llm_token_throughput` 6종을 기본 관측 지표로 고정한다. 추가는 본 문서 개정 필요.

- [ ] 6개 지표 수집 코드 존재
- [ ] 추가 지표 개정 PR 규약
- [ ] 주간 리뷰 항목에 포함

## Eval / Observability

### G-E1. 일일 리포트

`scripts/report_daily.py`가 24h 집계를 markdown으로 생성해 `logs/report/YYYY-MM-DD.md`에 저장한다. Grafana 등 외부 도구 도입 금지. 리뷰는 markdown + 주간 수기 정리로 수행한다.

- [ ] report_daily.py 작성
- [ ] 크론 등록 (Phase 3)
- [ ] 주간 리뷰 템플릿

### G-E2. 알림 임계값

`outbox_lag > 30m`, `fetch_success_rate < 0.8`, `extract_failure_rate > 0.2` 중 하나 해당 시 `logs/alerts.log`에 append한다. 외부 알림(Slack 등) 연동은 Phase 4 이후 논의.

- [ ] 임계값 상수 정의
- [ ] alerts.log 로테이션 정책
- [ ] 임계값 변경 이력 기록

## Protocol

### G-P1. 임계값 조정

임계값 변경은 최근 7일 `metrics` 데이터를 근거로 PR에 첨부한다. 근거 없는 조정은 리뷰어가 차단. 조정 후 24h 관찰 기간을 필수로 두고 회귀 시 즉시 롤백한다.

- [ ] PR 템플릿에 7일 지표 란
- [ ] 24h 관찰 로그 기록
- [ ] 롤백 절차 run-book

## Governance

### G-G1. 자동 게시 게이트 임계값

`AUTO_PUBLISH_THRESHOLD` 기본값 0.75. 변경은 사용자 명시 승인 필요. 전역 비활성화는 `.env`의 `AUTO_PUBLISH_DISABLED=1`로만 가능하며 코드 하드코딩 금지.

- [ ] 임계값 .env 주입
- [ ] 하드코딩 검출 hook
- [ ] 승인 이력 로그 보관

### G-G2. 평가 정의 변경 책임

점수 정의·지표 목록 변경은 본 문서 개정과 동시에 재계산 배치·대시보드 마이그레이션이 포함된 PR로만 허용한다. 부분 적용 금지.

- [ ] PR 체크리스트에 재계산 항목
- [ ] 부분 적용 차단 CI 규칙

## 변경 기록

- 2026-04-20 초안 작성.
