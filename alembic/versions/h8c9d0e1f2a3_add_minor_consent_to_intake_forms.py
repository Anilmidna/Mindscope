"""add_minor_consent_to_intake_forms

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'h8c9d0e1f2a3'
down_revision = 'g7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('intake_forms', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('intake_forms', sa.Column('parent_email', sa.String(254), nullable=True))
    op.add_column('intake_forms', sa.Column('minor_consent_pending', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('intake_forms', 'minor_consent_pending')
    op.drop_column('intake_forms', 'parent_email')
    op.drop_column('intake_forms', 'date_of_birth')
