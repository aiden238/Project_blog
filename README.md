# Project_Blog — 기술/AI 인사이트 블로그 자동화 시스템

## 프로젝트 개요

기술·AI 분야의 1차 출처(공식 블로그·릴리즈·연구 발표)와 2차 출처(뉴스·해설·커뮤니티)를 자동 수집해 **초안을 생산하고 리서치 재료를 정리**하는 자동화 시스템입니다.

최종 완성글의 100% 자동 발행이 아닌, **자동 초안 생산 + 리서치 보조**에 집중합니다. 최종 편집은 사람이 직접 수행합니다.

---

## 설계 원칙

```
1. LocalFS는 primary write, Notion은 Outbox 기반 projection이다.
2. Postgres = 메타 SoT, LocalFS = 콘텐츠 SoT, Notion ≠ SoT.
3. 자동 게시는 track=A ∧ license_class=first_party ∧ auto_publish_allowed=true ∧ score≥threshold 4중 AND에서만 허용.
```

- **무료 우선** — 상용 API는 명시적 옵션 어댑터, 기본 경로 아님
- **최소 종속성** — MIT/Apache-2.0 계열만 기본 채택
- **교체 가능한 어댑터 구조** — 특정 SaaS에 코어가 묶이지 않음
- **로컬 모델 우선** — Ollama + Gemma 3 12B 기반 추론

---

## 두 가지 트랙

### 트랙 A — 1차 출처 자동 초안
| 단계 | 내용 |
|---|---|
| 수집 | 공식 블로그 RSS, GitHub 릴리즈, 연구 발표 |
| 처리 | 본문 추출 → 정제 → 중복 제거 → 분류 → 요약 → 초안 생성 |
| 출력 | Notion DB 적재 (조건 통과 시 Tistory 게시) |

### 트랙 B — 2차 출처 리서치 보조
| 단계 | 내용 |
|---|---|
| 수집 | 개인 블로그, 뉴스, 해설, 커뮤니티 |
| 처리 | 수집 → 태깅 → 클러스터링 → 공통 주장/차이점 정리 |
| 출력 | Notion DB 적재 (수동 글 작성 재료) |

---

## 저장 구조

```
Postgres        ← 메타데이터 SoT (url, hash, status, tags, cluster_id, score)
LocalFS         ← 콘텐츠 SoT   (raw, clean, summaries, drafts)
Notion DB       ← 운영 UI      (검토 카드, 상태 토글, 링크만)
Tistory         ← 게시 채널    (Phase 4 옵션 어댑터)
```

---

## 기술 스택

| 영역 | 채택 | 라이선스 |
|---|---|---|
| 언어 | Python 3.11+ | — |
| 패키지 관리 | uv | MIT |
| DB | PostgreSQL 15 + pgvector | PostgreSQL |
| ORM/마이그레이션 | SQLAlchemy + Alembic | MIT |
| HTTP/Feed | httpx + feedparser | BSD |
| 본문 추출 | trafilatura + selectolax | Apache-2.0/MIT |
| 중복 제거 | datasketch (MinHash/SimHash) | MIT |
| 스케줄러 | APScheduler | MIT |
| 로컬 LLM | Ollama + Gemma 3 12B | MIT |
| 로깅 | structlog | Apache-2.0 |
| 설정 | pydantic-settings | MIT |

**배제**: LangChain, MinIO(AGPL), Airflow/Prefect/Dagster, newspaper3k

---

## 구현 단계

| Phase | 목표 | 완료 조건 |
|---|---|---|
| **0 — Foundation** | Postgres 스키마·Source Registry·설정 로더 구축 | `pipeline sources list` 3개 이상 출처 반환 |
| **1 — Collection** | 수집·본문 추출·중복 제거 | 10건 이상 clean 상태 저장 |
| **2 — LLM & Notion** | 로컬 LLM 초안 생성 + Outbox Notion projection | Notion에 초안 카드 10건 이상 자동 적재 |
| **3 — Stabilization** | APScheduler 무인 운영 + 백업 + DLQ 보강 | 24h 무인 실행 후 신규 카드 자동 적재 |
| **4 — Extension** | Tistory 어댑터 + pgvector 유사도 검색 | 4중 AND 게이트 통과 시 자동 게시 |

---

## 프로젝트 구조

```
Project_Blog/
├── CLAUDE.md               # 지침 라우터
├── instructions/           # Phase별 / 공통 기반 지침 파일
│   ├── tech_stack.md
│   ├── folder_structure.md
│   ├── eval_framework.md
│   ├── phase_0_foundation.md
│   ├── phase_1_collection.md
│   ├── phase_2_llm_notion.md
│   ├── phase_3_stabilization.md
│   ├── phase_4_extension.md
│   └── error_log.md        # 에이전트 자동 참조 금지
├── src/                    # 파이프라인 소스
├── sources/                # 출처 YAML (SoT)
├── db/migrations/          # Alembic 마이그레이션
├── docker/                 # Postgres + 서비스 컨테이너
├── scripts/                # 검증·리포트·백업 스크립트
├── data/                   # 수집·산출물 (gitignore)
└── docs/                   # license_audit 등 문서
```

---

## 빠른 시작

```bash
# 1. 환경 설정
cp .env.example .env   # 값 채우기

# 2. DB 기동
docker compose -f docker/compose.yml up -d postgres

# 3. 의존성 설치
uv sync

# 4. DB 마이그레이션
uv run alembic upgrade head

# 5. 출처 등록
uv run python -m pipeline sources sync

# 6. 수집 테스트
uv run python -m pipeline fetch --source openai_blog --dry-run
```

---

## 라이선스

MIT

---

> 본 시스템은 초안 생산 보조 도구입니다. 사실 검증과 최종 발행은 사람이 수행합니다.
