# Phase 3 — Stabilization

## Context

Phase 3은 파이프라인을 24h 무인 운영 가능한 수준으로 안정화한다. APScheduler 스케줄링, Outbox DLQ 보강, 주기 백업, 장애·드리프트 감지를 포함한다. 신규 기능 추가는 Phase 4 몫이며 본 단계는 운영 신뢰도 확보가 목표다.

## Harness / Environment

### G-H1. APScheduler 구성

`src/scheduler/main.py`에서 BlockingScheduler로 출처별 interval 작업을 등록한다. job_id 규칙 `fetch_<source_id>`, misfire_grace_time 300초. 컨테이너·시스템 재시작 시 자동 복구되도록 docker-compose에 통합한다.

- [ ] BlockingScheduler 기동 스크립트
- [ ] job_id 중복 방지
- [ ] misfire 로그 저장
- [ ] 재시작 자동 복구 검증

### G-H2. 로컬 백업

매일 03:00 KST에 `pg_dump`와 `data/` 스냅샷(tar.zst)을 생성해 `data/backups/YYYY-MM-DD/`에 저장한다. 보관 기간 14일. 복구 스크립트 `scripts/restore.sh`를 동봉하고 리허설 로그를 보존한다.

- [ ] 백업 크론 잡 등록
- [ ] 14일 초과 자동 정리
- [ ] restore.sh 리허설 실시
- [ ] 리허설 로그 경로 고정

## Meta

### G-M1. 작업 식별자 규약

모든 scheduled job·worker·manual run은 UUID `run_id`를 부여한다. `metrics.meta.run_id`와 `logs/*.log` 양쪽에 동일 값을 기록해 교차 조회 가능하게 한다. grep 한 번으로 전체 경로 추적 가능해야 한다.

- [ ] run_id 생성 유틸
- [ ] 모든 진입점에서 주입
- [ ] grep 교차 검증 테스트

## Eval / Observability

### G-E1. Liveness / Progress 감시

Outbox가 비어 있지 않은데 30분 이상 진행이 없으면 `stuck`으로 간주해 `logs/alerts.log`에 기록한다. 동일 run_id에서 같은 단계 실패가 3회 반복되면 drift 징후로 분류해 별도 라인으로 남긴다.

- [ ] stuck 감지 루틴
- [ ] drift 분류 규칙
- [ ] alerts.log 로테이션 정책

### G-E2. 파이프라인 지연 감시

각 단계 p95 레이턴시를 일일 리포트에 포함한다. 수집→정제 p95 > 5m 또는 LLM 생성 p95 > 3m가 7일 연속이면 튜닝 권고 항목으로 자동 노출한다.

- [ ] 단계별 p95 집계 쿼리
- [ ] 권고 항목 자동 생성
- [ ] 튜닝 이력 보존 경로

## Protocol

### G-P1. DLQ 처리 절차

`outbox.status='dead'`는 일일 리포트에 포함한다. 사용자가 `pipeline outbox inspect <id>`로 원인 확인 후 `replay` 또는 `discard`를 결정한다. 자동 discard는 금지하며 모든 결정은 이력에 기록한다.

- [ ] inspect 커맨드 구현
- [ ] replay/discard 이력 로깅
- [ ] 자동 discard 차단 테스트

### G-P2. 장애 기록 프로토콜

오류·드리프트·무한 루프 의심 사건은 `instructions/error_log.md`에 사용자가 직접 기록한다. 에이전트는 해당 파일을 자동 참조하지 않으며 사용자가 명시적으로 요청할 때만 열람한다. 기록은 최신이 위.

- [ ] error_log.md 템플릿 존재 확인
- [ ] 자동 참조 금지 헤더 확인
- [ ] 기록 순서 규약 준수 체크

## Governance

### G-G1. 백업 미검증 시 릴리스 금지

`restore.sh` 리허설이 최근 30일 내 통과 로그 없으면 Phase 4 기능 배포를 차단한다. 리허설 로그는 `data/backups/restore_drills/`에 축적하고 CI가 최신 로그 날짜를 확인한다.

- [ ] 리허설 로그 경로 생성
- [ ] 30일 초과 시 CI 차단
- [ ] 리허설 run-book 작성

### G-G2. 운영 변경 동결 기간

야간 03:00~05:00 KST는 백업 수행 시간으로 파이프라인·DDL 변경 배포를 동결한다. 불가피한 긴급 배포는 사용자 승인과 사전 백업 확인을 요구한다.

- [ ] 배포 스크립트에 시간대 가드
- [ ] 긴급 배포 승인 경로
- [ ] 동결 기간 로그 기록

## 변경 기록

- 2026-04-20 초안 작성.
- 2026-04-26 구현 현황 점검. 체크 반영 가능한 구현 항목은 아직 없음.
