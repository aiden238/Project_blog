from __future__ import annotations

from src.db import SessionLocal
from src.reporting import build_fetch_health_report


def build_report() -> str:
    session = SessionLocal()
    try:
        return build_fetch_health_report(session)
    finally:
        session.close()


def main() -> int:
    print(build_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
