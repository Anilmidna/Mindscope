"""add b2b_licenses and user_licenses tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'b2b_licenses',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_name', sa.String(200), nullable=False),
        sa.Column('context_of_origin', sa.String(50), nullable=False),
        sa.Column('total_licenses', sa.Integer, nullable=False),
        sa.Column('used_licenses', sa.Integer, nullable=False, server_default='0'),
        sa.Column('invite_code', sa.String(64), unique=True, nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_b2b_licenses_invite_code', 'b2b_licenses', ['invite_code'])

    op.create_table(
        'user_licenses',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('license_id', sa.UUID(as_uuid=True), sa.ForeignKey('b2b_licenses.id'), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_user_licenses_user_id', 'user_licenses', ['user_id'])


def downgrade() -> None:
    op.drop_table('user_licenses')
    op.drop_table('b2b_licenses')
