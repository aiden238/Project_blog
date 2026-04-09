# Alembic Runbook

## Rollback 절차

1. `alembic current`로 현재 revision을 확인한다.
2. 실패 직후 로그를 `logs/alembic/verify_schema.log`와 Alembic stderr에서 수집한다.
3. 마지막 정상 revision으로 `alembic downgrade <revision>`을 실행한다.
4. `scripts/verify_schema.py`를 다시 실행해 스키마를 검증한다.
5. 원인을 수정하기 전까지 동일 revision 재시도는 금지한다.

## 로그 규약

- 검증 결과는 `logs/alembic/verify_schema.log`에 JSON line으로 append한다.
- 필드: `checked_at`, `status`, `errors`
- `status=failed`면 rollback 근거 로그로 사용한다.
