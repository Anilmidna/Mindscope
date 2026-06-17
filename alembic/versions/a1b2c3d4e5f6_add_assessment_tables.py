"""add assessment tables: sessions, intake_forms, responses, scores, reports, bias_flags, norm_groups, section_timers

Revision ID: a1b2c3d4e5f6
Revises: 8caaef524476
Create Date: 2026-06-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8caaef524476'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sessions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('context_of_origin', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='started'),
        sa.Column('norm_group_id', sa.String(50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scoring_engine_version', sa.String(20), nullable=True),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])

    op.create_table(
        'intake_forms',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), unique=True, nullable=False),
        sa.Column('life_stage', sa.String(100), nullable=True),
        sa.Column('current_role', sa.String(200), nullable=True),
        sa.Column('current_field', sa.String(200), nullable=True),
        sa.Column('satisfaction_rating', sa.Integer, nullable=True),
        sa.Column('goals', sa.Text, nullable=True),
        sa.Column('challenges', sa.Text, nullable=True),
        sa.Column('background_tags', sa.String(500), nullable=True),
        sa.Column('years_of_experience', sa.String(50), nullable=True),
        sa.Column('highest_education', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'responses',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), nullable=False),
        sa.Column('item_id', sa.String(50), nullable=False),
        sa.Column('answer', sa.Integer, nullable=False),
        sa.Column('response_time_ms', sa.Integer, nullable=True),
        sa.Column('domain', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_responses_session_id', 'responses', ['session_id'])
    op.create_index('ix_responses_session_domain', 'responses', ['session_id', 'domain'])

    op.create_table(
        'scores',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), unique=True, nullable=False),
        sa.Column('riasec_r', sa.Float, nullable=True),
        sa.Column('riasec_i', sa.Float, nullable=True),
        sa.Column('riasec_a', sa.Float, nullable=True),
        sa.Column('riasec_s', sa.Float, nullable=True),
        sa.Column('riasec_e', sa.Float, nullable=True),
        sa.Column('riasec_c', sa.Float, nullable=True),
        sa.Column('ocean_o', sa.Float, nullable=True),
        sa.Column('ocean_c', sa.Float, nullable=True),
        sa.Column('ocean_e', sa.Float, nullable=True),
        sa.Column('ocean_a', sa.Float, nullable=True),
        sa.Column('ocean_n', sa.Float, nullable=True),
        sa.Column('apt_logical', sa.Float, nullable=True),
        sa.Column('apt_numerical', sa.Float, nullable=True),
        sa.Column('apt_verbal', sa.Float, nullable=True),
        sa.Column('apt_spatial', sa.Float, nullable=True),
        sa.Column('percentiles', JSONB, nullable=True),
        sa.Column('scoring_engine_version', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), unique=True, nullable=False),
        sa.Column('s3_url', sa.Text, nullable=True),
        sa.Column('prompt_template_version', sa.String(20), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'norm_groups',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('context', sa.String(50), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('sample_size', sa.Integer, nullable=True),
        sa.Column('score_stats', JSONB, nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'bias_flags',
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), primary_key=True),
        sa.Column('attention_check_result', sa.Boolean, nullable=True),
        sa.Column('social_desirability_score', sa.Float, nullable=True),
        sa.Column('response_time_outlier_flag', sa.Boolean, nullable=True),
        sa.Column('flagged_for_review', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'section_timers',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', sa.UUID(as_uuid=True), sa.ForeignKey('sessions.id'), nullable=False),
        sa.Column('domain', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('time_limit_seconds', sa.Integer, nullable=False),
    )
    op.create_index('ix_section_timers_session_domain', 'section_timers', ['session_id', 'domain'], unique=True)


def downgrade() -> None:
    op.drop_table('section_timers')
    op.drop_table('bias_flags')
    op.drop_table('norm_groups')
    op.drop_table('reports')
    op.drop_table('scores')
    op.drop_table('responses')
    op.drop_table('intake_forms')
    op.drop_table('sessions')
