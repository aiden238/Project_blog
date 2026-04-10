# Risk Register

에이전트 작업 리스크를 기록한다. 사용자 사건 기록은 `instructions/error_log.md` 범위를 따른다.

| id | phase | status | symptom | impact | mitigation | next_action | evidence | updated_at |
|---|---|---|---|---|---|---|---|---|
| R-2026-04-26-01 | Phase 1 | open | `openai_blog` 기사 본문 URL이 다수 `403`을 반환해 원문 fetch가 막힌다. 현재는 RSS `summary` 폴백으로만 clean 아이템을 생성한다. | 본문 깊이·코드블록·헤딩 품질이 낮아지고, article fetch 실패가 누적돼 출처 건강도 판단이 왜곡된다. | RSS 엔트리 `summary/content` 폴백 구현으로 clean 저장은 유지했다. | OpenAI 전용 추출 전략 또는 공식 API/대체 본문 경로를 검토하고, feed 성공과 article 실패 지표를 분리한다. | `pipeline fetch --source openai_blog`; `pipeline report fetch-health`; `data/clean/openai_blog/*` | 2026-04-26 |
| R-2026-04-26-02 | Phase 1 | open | `anthropic_news`의 현재 RSS endpoint가 `404`를 반환한다. | 출처 수집이 전혀 진행되지 않고 fetch health에서 disable 제안이 계속 발생한다. | 기존 endpoint는 유지하되 리스크로 고정하고 자동 게시/후속 단계 진입 근거로 사용하지 않는다. | Anthropic의 유효한 first-party feed 또는 대체 수집 경로를 확인해 `sources/anthropic_news.yaml`을 교체한다. | `Invoke-WebRequest https://www.anthropic.com/rss.xml`; `pipeline report fetch-health` | 2026-04-26 |
| R-2026-04-26-03 | Phase 1 | mitigated | 작업 경로에 한글이 포함돼 기본 `.venv`에서 `uv run` 및 Python site 초기화가 `UnicodeDecodeError`로 실패한다. | 로컬 검증 재현성이 떨어지고 기본 개발 흐름이 깨진다. | ASCII 경로의 별도 검증 venv(`C:\\temp\\blog_phase1_verify2`)에서 테스트와 CLI를 실행했다. | 기본 개발 환경을 ASCII 경로로 이동하거나 venv/툴체인 인코딩 우회 절차를 문서화한다. | `uv run pytest -q`; `C:\\temp\\blog_phase1_verify2\\Scripts\\python.exe -m pytest -q` | 2026-04-26 |
