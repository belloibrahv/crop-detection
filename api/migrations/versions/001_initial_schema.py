"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'farmer',
        sa.Column('farmer_id', sa.String(36), primary_key=True),
        sa.Column('device_identifier', sa.String(128), nullable=False, unique=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('preferred_language', sa.String(20), server_default='en'),
        sa.Column('registration_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'disease_class',
        sa.Column('class_id', sa.Integer(), primary_key=True),
        sa.Column('crop_name', sa.String(50), nullable=False),
        sa.Column('disease_name', sa.String(100), nullable=False),
        sa.Column('is_healthy', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.UniqueConstraint('crop_name', 'disease_name', name='_crop_disease_uc'),
    )

    op.create_table(
        'treatment_advisory',
        sa.Column('advisory_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('class_id', sa.Integer(), sa.ForeignKey('disease_class.class_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('local_treatment_options', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'admin',
        sa.Column('admin_id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(120), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(30), server_default='admin'),
    )

    op.create_table(
        'diagnosis_record',
        sa.Column('diagnosis_id', sa.String(36), primary_key=True),
        sa.Column('farmer_id', sa.String(36), sa.ForeignKey('farmer.farmer_id', ondelete='CASCADE'), nullable=False),
        sa.Column('image_thumbnail_url', sa.String(255), nullable=True),
        sa.Column('predicted_class_id', sa.Integer(), sa.ForeignKey('disease_class.class_id'), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('top3_predictions', sa.JSON(), nullable=True),
        sa.Column('retrain_consent', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_diagnosis_farmer', 'diagnosis_record', ['farmer_id', 'created_at'])

    op.create_table(
        'audit_log',
        sa.Column('log_id', sa.String(36), primary_key=True),
        sa.Column('admin_id', sa.String(36), sa.ForeignKey('admin.admin_id'), nullable=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('target_table', sa.String(50), nullable=True),
        sa.Column('diff', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_index('idx_diagnosis_farmer', table_name='diagnosis_record')
    op.drop_table('diagnosis_record')
    op.drop_table('admin')
    op.drop_table('treatment_advisory')
    op.drop_table('disease_class')
    op.drop_table('farmer')
