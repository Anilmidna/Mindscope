"""add jti and user_id columns to refresh_token_blocklist

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-07-02

The original blocklist migration only created token_hash.
auth_service.py queries by jti and bulk-revokes by user_id,
so both columns are required for the refresh/logout/reuse-detection flow.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i9d0e1f2a3b4'
down_revision: Union[str, None] = 'h8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('refresh_token_blocklist', sa.Column('jti', sa.String(36), nullable=True))
    op.add_column('refresh_token_blocklist', sa.Column('user_id', sa.String(36), nullable=True))
    op.create_index('ix_refresh_token_blocklist_jti', 'refresh_token_blocklist', ['jti'], unique=True)
    op.create_index('ix_refresh_token_blocklist_user_id', 'refresh_token_blocklist', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_refresh_token_blocklist_user_id', table_name='refresh_token_blocklist')
    op.drop_index('ix_refresh_token_blocklist_jti', table_name='refresh_token_blocklist')
    op.drop_column('refresh_token_blocklist', 'user_id')
    op.drop_column('refresh_token_blocklist', 'jti')
