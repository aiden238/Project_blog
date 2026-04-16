# Folder Structure

## Context

LocalFS는 콘텐츠 SoT다. 디렉터리 구조는 수집·정제·초안 단계가 한눈에 보이도록 단계별로 분리한다. raw와 산출물은 절대 같은 폴더에 두지 않으며 원본 불변 원칙을 강제한다.

## Harness / Environment

### G-H1. 최상위 트리

프로젝트 루트는 아래 구조를 유지한다. 추가 최상위 디렉터리는 본 문서 개정을 선행한 PR에서만 허용한다.

```
Project_Blog/
├── CLAUDE.md
├── instructions/
├── src/
├── sources/          # 출처 YAML (SoT)
├── db/migrations/
├── docker/
├── scripts/
├── tests/
├── data/
├── docs/
└── logs/
```

- [ ] 최상위 디렉터리 생성 확인
- [ ] `sources/` 경로 확정
- [ ] 추가 생성 차단 CI 규칙

### G-H2. data/ 하위 구조

수집·정제·산출물은 단계별 분리한다. 단계 간 파일 이동·복사 금지. 복원·재수집은 파이프라인 커맨드로만 수행한다.

```
data/
├── raw/<source_id>/
├── clean/<source_id>/
├── summaries/
├── drafts/track_a/
├── drafts/track_b/
├── html/
└── backups/
    └── restore_drills/
```

- [ ] raw/clean/summaries/drafts 분리
- [ ] backups 경로 전용 보장
- [ ] 단계 이동 시 커맨드 경유

## Meta

### G-M1. 파일명 규칙

모든 수집 아이템은 `<UTC_ISO>_<source_id>_<short_hash>.<ext>`로 저장한다. 공백·한글·특수문자 금지. 경로는 ASCII·언더스코어·하이픈만 사용하고 대문자는 확장자 제외 금지.

- [ ] 파일명 lint 스크립트 작성
- [ ] 위반 파일 탐지·격리 경로 정의
- [ ] short_hash 길이 상수 결정 (기본 12)

### G-M2. 원본 불변성

`data/raw/` 저장 파일은 읽기 전용으로 취급한다. 수정·덮어쓰기·삭제 금지. 오염된 원본은 `data/raw_quarantine/`로 이동해 격리하며 재수집은 신규 파일로만 추가한다.

- [ ] raw/ 권한 적용 (읽기 전용)
- [ ] quarantine 디렉터리 상시 존재
- [ ] 덮어쓰기 차단 단위 테스트

## Eval / Observability

### G-E1. 구조 검증 스크립트

`scripts/check_layout.py`가 디렉터리 존재·권한·명명 규칙을 점검하고 실패 시 exit 1을 반환한다. CI에서 매 빌드 실행하며 로컬도 pre-push hook에 등록한다.

- [ ] check_layout.py 작성
- [ ] CI job 등록
- [ ] pre-push hook 설정
- [ ] 실패 케이스 스냅샷 테스트

## Protocol

### G-P1. 신규 디렉터리 추가

새 최상위·중간 디렉터리 추가는 본 문서 개정을 선행하는 PR에서만 허용한다. 문서 변경 없이 생성된 디렉터리는 CI가 실패 처리하며 자동 정리하지 않는다.

- [ ] 문서 개정 PR 선행 규약
- [ ] 구조 lint CI 차단 동작 확인
- [ ] 임시 디렉터리 정책 별도 문서화

## Governance

### G-G1. 금지 저장 위치

시크릿·개인정보는 리포지토리 내 어디에도 저장하지 않는다. 로컬 `.env`와 `~/.config/blog_automation/secrets.toml`로 한정. `data/`에 개인정보 유입 감지 시 즉시 `raw_quarantine/`로 격리한다.

- [ ] `.gitignore`에 .env·secrets 포함
- [ ] 시크릿 스캐너 hook 등록
- [ ] 격리 절차 run-book 작성

## 변경 기록

- 2026-04-20 초안 작성.
