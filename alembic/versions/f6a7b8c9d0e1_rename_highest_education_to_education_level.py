"""rename highest_education to education_level in intake_forms

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-19

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('intake_forms', 'highest_education', new_column_name='education_level')


def downgrade() -> None:
    op.alter_column('intake_forms', 'education_level', new_column_name='highest_education')
