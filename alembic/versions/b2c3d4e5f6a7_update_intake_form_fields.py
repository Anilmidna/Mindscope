"""update intake_forms to match persona_intake spec

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old columns that don't match spec
    op.drop_column('intake_forms', 'current_role')
    op.drop_column('intake_forms', 'current_field')
    op.drop_column('intake_forms', 'satisfaction_rating')
    op.drop_column('intake_forms', 'background_tags')
    op.drop_column('intake_forms', 'years_of_experience')
    op.drop_column('intake_forms', 'goals')

    # Make life_stage non-nullable (required field)
    op.alter_column('intake_forms', 'life_stage', nullable=False, server_default=None)

    # Add new columns
    op.add_column('intake_forms', sa.Column('persona', sa.String(20), nullable=False, server_default='student'))
    op.add_column('intake_forms', sa.Column('domain', sa.String(200), nullable=True))
    op.add_column('intake_forms', sa.Column('specialization', sa.String(100), nullable=True))
    op.add_column('intake_forms', sa.Column('future_goals', sa.Text, nullable=True))
    op.add_column('intake_forms', sa.Column('satisfaction', sa.Integer, nullable=True))
    op.add_column('intake_forms', sa.Column('preferred_work_style', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('intake_forms', 'preferred_work_style')
    op.drop_column('intake_forms', 'satisfaction')
    op.drop_column('intake_forms', 'future_goals')
    op.drop_column('intake_forms', 'specialization')
    op.drop_column('intake_forms', 'domain')
    op.drop_column('intake_forms', 'persona')
    op.add_column('intake_forms', sa.Column('goals', sa.Text, nullable=True))
    op.add_column('intake_forms', sa.Column('years_of_experience', sa.String(50), nullable=True))
    op.add_column('intake_forms', sa.Column('background_tags', sa.String(500), nullable=True))
    op.add_column('intake_forms', sa.Column('satisfaction_rating', sa.Integer, nullable=True))
    op.add_column('intake_forms', sa.Column('current_field', sa.String(200), nullable=True))
    op.add_column('intake_forms', sa.Column('current_role', sa.String(200), nullable=True))
