"""Add phase2 llm and outbox status

Revision ID: 61d7f83f5c0e
Revises: 09a64bf9b2ea
Create Date: 2026-04-26 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "61d7f83f5c0e"
down_revision: Union[str, Sequence[str], None] = "09a64bf9b2ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE outbox
        SET status = CASE
            WHEN status = 'dispatched' THEN 'sent'
            WHEN status = 'dead_letter' THEN 'dead'
            ELSE status
        END
        """
    )
    op.drop_constraint("ck_items_status", "items", type_="check")
    op.create_check_constraint(
        "ck_items_status",
        "items",
        "status IN ('raw', 'clean', 'extract_failed', 'llm_failed', 'summarized', 'draft_ready', 'published')",
    )
    op.drop_constraint("ck_outbox_status", "outbox", type_="check")
    op.create_check_constraint(
        "ck_outbox_status",
        "outbox",
        "status IN ('pending', 'processing', 'sent', 'failed', 'dead')",
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE outbox
        SET status = CASE
            WHEN status = 'sent' THEN 'dispatched'
            WHEN status = 'dead' THEN 'dead_letter'
            ELSE status
        END
        """
    )
    op.drop_constraint("ck_outbox_status", "outbox", type_="check")
    op.create_check_constraint(
        "ck_outbox_status",
        "outbox",
        "status IN ('pending', 'processing', 'dispatched', 'failed', 'dead_letter')",
    )
    op.drop_constraint("ck_items_status", "items", type_="check")
    op.create_check_constraint(
        "ck_items_status",
        "items",
        "status IN ('raw', 'clean', 'extract_failed', 'summarized', 'draft_ready', 'published')",
    )
