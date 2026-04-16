# License Audit

신규 의존성 추가 시 이 파일에 라이선스·버전·용도를 기록한다.
GPL·AGPL 검출 시 즉시 제거하고 대안을 기록한다.

## 화이트리스트 기준

- 허용: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause
- 조건부: LGPL (동적 링크 전제에서만)
- 금지: GPL, AGPL

## 의존성 목록

| 패키지 | 버전 | 라이선스 | 용도 | 확인일 |
|---|---|---|---|---|
| httpx | >=0.27.0 | BSD | HTTP 클라이언트 | 2026-04-20 |
| feedparser | >=6.0.11 | BSD | RSS/Atom 파싱 | 2026-04-20 |
| trafilatura | >=1.9.0 | Apache-2.0 | 본문 추출 | 2026-04-20 |
| selectolax | >=0.3.17 | MIT | HTML 파싱 | 2026-04-20 |
| sqlalchemy | >=2.0.0 | MIT | ORM | 2026-04-20 |
| alembic | >=1.13.0 | MIT | DB 마이그레이션 | 2026-04-20 |
| psycopg2-binary | >=2.9.9 | LGPL (동적) | Postgres 드라이버 | 2026-04-20 |
| pydantic-settings | >=2.3.0 | MIT | 설정 로더 | 2026-04-20 |
| datasketch | >=1.6.5 | MIT | MinHash/SimHash | 2026-04-20 |
| apscheduler | >=3.10.4 | MIT | 작업 스케줄러 | 2026-04-20 |
| pyyaml | >=6.0.1 | MIT | YAML 파싱 | 2026-04-20 |
| jsonschema | >=4.23.0 | MIT | 스키마 검증 | 2026-04-20 |
| structlog | >=24.1.0 | Apache-2.0/MIT | 구조화 로깅 | 2026-04-20 |

## 배제 항목

| 패키지 | 이유 |
|---|---|
| langchain | 과도한 종속성, breaking change 빈번 |
| minio | AGPL-3.0 금지 |
| newspaper3k | 유지보수 부진 |
| airflow | 초기 오버킬 |
| prefect | 초기 오버킬 |
