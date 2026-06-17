"""add account_type to users, flow_type + persona_tag to sessions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users: b2c vs b2b
    op.add_column('users', sa.Column('account_type', sa.String(20), nullable=False, server_default='b2c'))

    # sessions: b2c vs b2b flow, persona routing tag
    op.add_column('sessions', sa.Column('flow_type', sa.String(20), nullable=False, server_default='b2c'))
    op.add_column('sessions', sa.Column('persona_tag', sa.String(20), nullable=True))

    # reports: store prompt template version for audit
    op.add_column('reports', sa.Column('raw_llm_json', sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column('reports', 'raw_llm_json')
    op.drop_column('sessions', 'persona_tag')
    op.drop_column('sessions', 'flow_type')
    op.drop_column('users', 'account_type')
