# Phase 1 — Collection

## Context

Phase 1은 수집·본문 추출·정제·중복 제거를 담당한다. 산출물은 `data/raw/`, `data/clean/`에 저장되고 메타는 `items`에 기록된다. LLM·Notion 연동은 Phase 2 영역이다. 이 단계 종료 시 10건 이상이 `clean` 상태여야 한다.

## Harness / Environment

### G-H1. Fetcher 구성

`httpx`로 HTTP, `feedparser`로 RSS, GitHub releases는 REST API 직접 호출로 수집한다. 타임아웃 30초 고정, 재시도 3회 지수 백오프. 세션은 모듈 단위 싱글톤으로 재사용한다.

- [ ] httpx 싱글톤 클라이언트
- [ ] feedparser 래퍼
- [ ] 타임아웃·재시도 `.env` 주입
- [ ] 세션 재사용 테스트

### G-H2. 본문 추출

1차 trafilatura, 실패 시 selectolax 기반 custom 파서로 폴백한다. 출처별 커스텀은 `src/extract/custom_<source_id>.py`에 배치. 추출 실패는 `items.status='extract_failed'`로 격리한다.

- [ ] trafilatura 래퍼 작성
- [ ] custom 파서 플러그인 로더
- [ ] 실패 상태 기록 확인
- [ ] 폴백 경로 단위 테스트

## Meta

### G-M1. ETag / Last-Modified

Fetcher는 이전 응답 ETag·Last-Modified를 `sources` 레코드에 저장하고 다음 요청의 조건부 헤더로 사용한다. 304 응답 시 fetch_count만 증가시키고 본문 저장·items 삽입은 수행하지 않는다.

- [ ] sources.etag 컬럼 추가
- [ ] 304 경로 통합 테스트
- [ ] fetch_count 증가 검증

### G-M2. canonical URL 정규화

URL은 쿼리 파라미터 정렬, 추적 파라미터(utm_*, fbclid, gclid) 제거, fragment 제거 규칙으로 정규화한다. 정규화 결과를 `items.canonical_url`에 저장하고 UNIQUE 제약으로 중복 삽입을 차단한다.

- [ ] normalize_url 함수 구현
- [ ] 추적 파라미터 블랙리스트 관리
- [ ] UNIQUE 위반 케이스 테스트

### G-M3. 원본 저장 경로 규약

원본은 `data/raw/<source_id>/<UTC_ISO>_<short_hash>.<ext>`에 저장한다. 확장자는 MIME 기반으로 결정하며 파일 생성과 동시에 `items.raw_path`에 절대 경로를 기록한다.

- [ ] MIME→확장자 매핑표
- [ ] raw_path 기록 트랜잭션
- [ ] 경로 문자열 lint

## Eval / Observability

### G-E1. 수집 실패 관측

각 fetch 시도는 `metrics`에 `kind='fetch'`로 기록한다. 출처별 7일 이동 평균 실패율을 일일 리포트에 포함하며 실패율 50% 초과 시 해당 출처의 disable 제안 항목을 자동으로 노출한다.

- [ ] fetch metric 기록 경로
- [ ] 이동 평균 산출 스크립트
- [ ] disable 제안 리포트 항목

### G-E2. 추출 품질 관측

추출 결과의 본문 길이, 헤딩 수, 코드블록 수를 `metrics`에 `kind='extract'`로 기록한다. 본문 50자 미만이면 자동 `extract_suspicious`로 플래그하고 리뷰 큐에 넣는다.

- [ ] extract metric 기록
- [ ] suspicious 플래그 동작 확인
- [ ] 리뷰 큐 테이블 정의

## Protocol

### G-P1. 중복 제거 절차

canonical URL 일치 시 즉시 skip. URL 불일치이면서 본문 SimHash 64bit 해밍 거리 ≤ 3이면 중복 처리. 임베딩 기반 중복 제거는 Phase 4에서 도입하며 Phase 1에는 넣지 않는다.

- [ ] SimHash 구현·테스트
- [ ] 해밍 거리 임계값 상수화
- [ ] 중복 판정 로그 저장

## Governance

### G-G1. robots.txt / ToS 준수

모든 fetcher는 출처별 robots.txt를 조회·준수한다. Disallow 경로 접근 금지. 출처 YAML에 `respect_robots: false`가 명시되지 않으면 robots 검사를 스킵할 수 없다.

- [ ] robots 파서 통합
- [ ] 위반 로그 기록
- [ ] 예외 출처 문서 근거 첨부

### G-G2. 수집량 상한

출처별 시간당 요청 수는 기본 60회 상한이다. YAML의 `fetch.rate_limit`로 조정 가능하되 기본 초과 시 경고 로그. 상한 제거는 본 문서 개정 선행 PR에서만 허용한다.

- [ ] rate limit 구현
- [ ] 초과 경고 로그
- [ ] 상한 제거 PR 규약

## 변경 기록

- 2026-04-20 초안 작성.
