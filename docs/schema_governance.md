# Schema Governance

## DDL 규칙

- 스키마 변경은 Alembic revision으로만 수행한다.
- `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE` 문자열을 애플리케이션 코드에 직접 넣지 않는다.
- 검증은 `scripts/lint_ddl.py`로 수행한다.

## DROP 체크리스트

1. 삭제 대상이 실제 운영 데이터에 쓰이는지 확인한다.
2. 최소 30일 deprecation 로그를 남긴다.
3. rollback 가능한 downgrade가 revision에 포함됐는지 확인한다.
4. 사용자 승인 후에만 DROP 계열 변경을 머지한다.

## Deprecation 로그 양식

```json
{
  "recorded_at": "2026-04-25T13:00:00Z",
  "kind": "schema_deprecation",
  "target": "items.old_column",
  "removal_after": "2026-05-25T13:00:00Z",
  "reason": "replaced by items.item_meta"
}
```
