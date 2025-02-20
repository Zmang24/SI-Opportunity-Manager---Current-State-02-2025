"""Add comments field to opportunities

Revision ID: 004
Revises: 003
Create Date: 2024-02-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade():
    # Add comments column to opportunities table
    op.add_column('opportunities', sa.Column('comments', JSONB, server_default='[]'))

def downgrade():
    # Remove comments column
    op.drop_column('opportunities', 'comments') 