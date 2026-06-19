"""add consent_given_at to intake_forms (DPDP Act compliance)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-26

consent_given_at is a legal requirement under India's DPDP Act.
The timestamp proves when the user explicitly accepted data processing.
This field must never be NULL for any completed intake.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: add column as nullable so existing rows don't violate the constraint
    op.add_column(
        'intake_forms',
        sa.Column('consent_given_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Step 2: backfill existing rows with created_at (best available proxy for consent time)
    op.execute(
        "UPDATE intake_forms SET consent_given_at = created_at WHERE consent_given_at IS NULL"
    )
    # Step 3: enforce NOT NULL going forward
    op.alter_column('intake_forms', 'consent_given_at', nullable=False)


def downgrade() -> None:
    op.drop_column('intake_forms', 'consent_given_at')
