# Work Log

## 세션 기록

---

### 2026-04-04

**작업 시간**: 23:36 KST

#### 1. 블로그 자동화 시스템 재기획안 검토

아래 핵심 목표를 기준으로 시스템 기획안을 수립했다.

- 완전 무료에 최대한 가깝고, 종속성이 낮고, 라이선스가 자유로운 구조
- 자동 초안 생산 + 리서치 재료 정리에 집중 (자동 발행 100%는 목표 아님)
- 최종 편집은 사람이 직접 수행

**결정 사항**:
- 트랙 A: 1차 출처 기반 자동 초안 생산 → Notion 기본 출력
- 트랙 B: 2차 출처 기반 수동 글 보조 → 인사이트 저장소
- 저장 구조: PostgreSQL(메타 SoT) + LocalFS(콘텐츠 SoT) + Notion(projection)
- Tistory는 코어 아님, 옵션 export 어댑터로 격리

---

#### 2. 설계 비판적 검토 (A/B 분석)

두 차례 분석을 비교해 B안의 구조적 판단을 주축으로 채택했다.

**채택된 핵심 원칙 3줄**:

```
1. LocalFS는 primary write, Notion은 Outbox 기반 projection이다.
2. Postgres = 메타 SoT, LocalFS = 콘텐츠 SoT, Notion ≠ SoT.
3. 자동 게시는 track=A ∧ license_class=first_party ∧ auto_publish_allowed=true ∧ score≥threshold 4중 AND일 때만 허용.
```

**GPT 결론 검토 결과**:
- 타당: "상용 API fallback은 옵션", Drive 초기 제외, 3-stack 시작
- 과함: "Tistory API 불안정 단정은 과했다" → 반론: 실제 불안정 상태이므로 원래 판단 유지
- 누락: Outbox 패턴, SoT 계층 명시, 4중 AND 게이트가 요약에서 희석됨

---

#### 3. 블로그 자동화 기획안 구성

상세 기획 문서를 인터랙티브하게 구성했다.

**최종 채택 구조**:
- PostgreSQL + LocalFS + Notion 3-stack으로 시작
- Drive는 당장 필수 아님 (나중에 S3 호환으로 추가)
- Source Registry: YAML(선언적 SoT) + Postgres(런타임 캐시)
- 출처 추가/수정: YAML 파일 편집 → `pipeline sources sync`

**확정된 5개 결정**:
1. Tistory API 앱 등록 가능 → Phase 4 옵션 어댑터로 구현
2. Gemma 3 12B + RTX 5070 Ti(16GB) → Q4_K_M 구동, VRAM 검증 필수
3. `auto_publish_allowed`는 사용자가 YAML로 직접 조정
4. 통합 Notion DB + 필터 뷰 (Track A / Track B / DLQ)
5. `AUTO_PUBLISH_THRESHOLD=0.75` 기본값, 추후 조정

---

#### 4. CLAUDE.md 라우터 및 지침 파일 세트 생성

`instructions/` 아래 10개 파일을 생성했다.

| 파일 | 내용 |
|---|---|
| `CLAUDE.md` | 라우터 (3줄 원칙 + 파일 라우팅 + 지침 규약) |
| `tech_stack.md` | Python/uv/Postgres/Ollama-Gemma3 12B 스택 정의 |
| `folder_structure.md` | LocalFS SoT 기반 디렉터리 구조 및 원본 불변 원칙 |
| `eval_framework.md` | 품질 점수·관측 지표·자동 게시 게이트 임계값 |
| `phase_0_foundation.md` | Alembic·Source Registry·설정 로더 구축 |
| `phase_1_collection.md` | Fetch·Extract·Dedupe (ETag·SimHash·canonical URL) |
| `phase_2_llm_notion.md` | Ollama 어댑터·Outbox 워커·통합 Notion DB |
| `phase_3_stabilization.md` | APScheduler·백업·DLQ·드리프트 감지 |
| `phase_4_extension.md` | Tistory·pgvector·4중 AND 게이트·feature flag |
| `error_log.md` | 에이전트 자동 참조 금지, 사용자 전용 기록 파일 |

**지침 설계 원칙**:
- 각 지침 본문 150~200자 이내 (초과 시 G-X1a/b 분할)
- 헤딩 H4 이하 계층 금지 (최대 4계층)
- 각 지침에 체크리스트 필수
- 6개 섹션 구조: Context / Harness·Environment / Meta / Eval·Observability / Protocol / Governance
- 육하원칙을 각 지침 본문에 자연스럽게 녹임
- Outbox 패턴, SKIP LOCKED, SimHash, 지수 백오프, 12-factor, feature flag 등 엔지니어링 기법 명시

---

#### 5. Project_Blog 디렉터리 구현

`C:/Users/songb/OneDrive/바탕 화면/Project_Blog` 에 전체 프로젝트 구조를 배포했다.

**생성된 파일/디렉터리**:
```
Project_Blog/
├── CLAUDE.md
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── instructions/         ← 지침 10개
├── sources/              ← YAML 3개 (openai_blog, anthropic_news, github_releases_llm)
├── src/
│   ├── config.py         ← pydantic-settings 기반 설정 로더
│   └── {llm,extract,workers,publish,scheduler,prompts}/
├── db/migrations/
├── docker/
│   ├── compose.yml       ← Postgres 15 + pgvector + 서비스 컨테이너
│   └── Dockerfile
├── scripts/
│   └── check_layout.py   ← 구조 검증 스크립트
├── docs/
│   └── license_audit.md
└── data/, logs/          ← gitignore 대상
```

---

#### 6. GitHub 저장소 생성 및 푸시

- 저장소: https://github.com/aiden238/Project_blog
- 커밋 날짜: 2026-04-16 21:37 KST (백데이트)
- 커밋 파일: 23개
- 브랜치: main

---

## 미결 항목

| 항목 | 우선순위 | 비고 |
|---|---|---|
| Gemma 3 12B VRAM 실측 | 🔴 High | Q4_K_M 기동 후 nvidia-smi로 측정 |
| `alembic init` + 4개 테이블 revision 작성 | 🔴 High | Phase 0 착수 조건 |
| `src/llm/ollama_client.py` 구현 | 🟠 Medium | Phase 2 전 필요 |
| Notion DB 생성 + NOTION_TOKEN 발급 | 🟠 Medium | Phase 2 전 필요 |
| Tistory 앱 등록·토큰 발급 | 🟡 Low | Phase 4에서 사용 |
| restore.sh 백업 리허설 | 🟡 Low | Phase 3 완료 조건 |
