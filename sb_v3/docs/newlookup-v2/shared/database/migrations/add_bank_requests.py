"""Add bank and brute bank type request tables

Revision ID: add_bank_requests
Revises: 
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_bank_requests'
down_revision = None  # Update this to your latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Create bank_type_requests table
    op.create_table(
        'bank_type_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('requested_name', sa.String(length=200), nullable=False),
        sa.Column('state', sa.String(length=10), nullable=True),
        sa.Column('zip', sa.String(length=20), nullable=True),
        sa.Column('has_docs', sa.Boolean(), nullable=False, default=False),
        sa.Column('doc_type', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('product_type', sa.String(length=20), nullable=True),
        sa.Column('product_subtype', sa.String(length=30), nullable=True),
        sa.Column('category', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ),
    )
    op.create_index(op.f('ix_bank_type_requests_seller_id'), 'bank_type_requests', ['seller_id'], unique=False)
    op.create_index(op.f('ix_bank_type_requests_status'), 'bank_type_requests', ['status'], unique=False)

    # Create brute_bank_type_requests table
    op.create_table(
        'brute_bank_type_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('requested_name', sa.String(length=200), nullable=False),
        sa.Column('bank_code', sa.String(length=100), nullable=True),
        sa.Column('attributes', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ),
    )
    op.create_index(op.f('ix_brute_bank_type_requests_seller_id'), 'brute_bank_type_requests', ['seller_id'], unique=False)
    op.create_index(op.f('ix_brute_bank_type_requests_status'), 'brute_bank_type_requests', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_brute_bank_type_requests_status'), table_name='brute_bank_type_requests')
    op.drop_index(op.f('ix_brute_bank_type_requests_seller_id'), table_name='brute_bank_type_requests')
    op.drop_table('brute_bank_type_requests')
    
    op.drop_index(op.f('ix_bank_type_requests_status'), table_name='bank_type_requests')
    op.drop_index(op.f('ix_bank_type_requests_seller_id'), table_name='bank_type_requests')
    op.drop_table('bank_type_requests')
