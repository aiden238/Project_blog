# Blog Automation — Instruction Router

본 파일은 라우터다. 실제 작업 지침은 `instructions/` 하위 파일을 우선한다.

## 3줄 원칙 (불가침)

1. LocalFS는 primary write, Notion은 Outbox 기반 projection이다.
2. Postgres = 메타 SoT, LocalFS = 콘텐츠 SoT, Notion ≠ SoT.
3. 자동 게시는 `track=A ∧ license_class=first_party ∧ auto_publish_allowed=true ∧ score≥threshold` 4중 AND에서만 허용.

## 파일 라우팅

### 공통 기반
- [기술 스택](instructions/tech_stack.md)
- [폴더 구조](instructions/folder_structure.md)
- [평가 프레임워크](instructions/eval_framework.md)

### 단계별
- [Phase 0 — Foundation](instructions/phase_0_foundation.md)
- [Phase 1 — Collection](instructions/phase_1_collection.md)
- [Phase 2 — LLM & Notion](instructions/phase_2_llm_notion.md)
- [Phase 3 — Stabilization](instructions/phase_3_stabilization.md)
- [Phase 4 — Extension](instructions/phase_4_extension.md)

## 자동 읽기 금지

- [error_log.md](instructions/error_log.md): 에이전트는 작업 중 자동 참조·grep·요약 대상으로 삼지 않는다. 사용자가 파일명을 명시하거나 "에러 로그 읽어"류로 요청할 때만 열람한다.

## 지침 작성 규칙

- 각 지침 본문은 150~200자 이내로 작성.
- 초과 시 `G-X1a`, `G-X1b`로 분할.
- 헤딩 계층은 H4(####) 이하로 제한.
- 각 지침 하단에 체크리스트 필수.
- 각 지침은 육하원칙을 본문에 녹여 기술.

## 섹션 규약

각 지침 파일은 아래 6개 섹션으로 구성한다.

1. Context
2. Harness / Environment
3. Meta
4. Eval / Observability
5. Protocol
6. Governance

## 충돌 해소

- 세부 지침과 라우터 지침 충돌 시 세부 지침이 우선.
- 단 "3줄 원칙"은 항상 상위.
- 세부 지침끼리 충돌 시 Phase 번호가 낮은 쪽이 기반 규약, 높은 쪽이 확장 규약으로 해석.

## 기준 시각

- 2026-04-20 기준 초안.
- 업데이트 시 각 파일 하단 `## 변경 기록` 갱신.
