# Risk Logging

## Context

리스크는 오류 사후기록과 분리 관리한다. 에이전트는 구현·검증·운영 중 확인한 제약과 우회 상태를 `docs/risk_register.md`에 기록해 다음 작업과 Phase 판단의 근거를 남긴다.

- [x] 리스크와 에러 기록 경계 명시
- [x] 작업 후 기록 대상 정의

## Harness / Environment

### G-H1. 기록 파일

에이전트가 유지하는 리스크 SoT는 `docs/risk_register.md`다. 출처 장애, 검증 제약, 계측 왜곡, 플랫폼 한계를 여기에 적고, 사용자 사건 타임라인은 `error_log.md`와 혼합하지 않는다.

- [x] `docs/risk_register.md` 사용
- [x] `error_log.md`와 역할 분리

## Meta

### G-M1. 레코드 필드

각 항목은 `id, phase, status, symptom, impact, mitigation, next_action, updated_at`을 포함한다. 같은 증상은 기존 항목을 갱신하고, 상태는 `open|mitigated|closed` 중 하나로 유지한다.

- [x] 필수 필드 고정
- [x] 상태 값 집합 고정

## Eval / Observability

### G-E1. 갱신 트리거

에이전트는 테스트 실패, 우회 적용, 외부 의존성 4xx/5xx, 계측 왜곡, 경로·플랫폼 제약을 확인하면 즉시 레지스터를 갱신한다. 각 항목엔 로그·명령·파일 근거를 1개 이상 남긴다.

- [x] 갱신 트리거 명시
- [x] 근거 필드 포함

## Protocol

### G-P1. 작업 종료 절차

의미 있는 코드·문서 변경이 끝나면 최종 요약 전 `docs/risk_register.md`를 먼저 갱신한다. 변경이 없으면 상태만 갱신하고 빈 리스크 생성은 금지하며, 새 Phase 착수 전 열린 리스크를 재검토한다.

- [x] 종료 전 기록 순서 고정
- [x] 빈 항목 생성 금지

## Governance

### G-G1. 책임 경계

`error_log.md`는 사용자 사건 기록, `risk_register.md`는 에이전트 작업 리스크 기록으로 분리한다. 규약 변경 시 라우터와 본 문서를 함께 개정하고, 에이전트는 `error_log.md` 자동 열람 금지 규칙을 유지한다.

- [x] 사용자/에이전트 책임 분리
- [x] 라우터 동시 개정 규칙

## 변경 기록

- 2026-04-26 초안 작성. 리스크 전용 기록 규약과 `docs/risk_register.md` 운영 기준 추가.
