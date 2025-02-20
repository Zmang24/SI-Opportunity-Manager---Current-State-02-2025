"""Add timing fields for work tracking

Revision ID: 002
Revises: 001
Create Date: 2024-02-14 18:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add started_at and work_time columns to opportunities table
    op.add_column('opportunities', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('opportunities', sa.Column('work_time', sa.Interval(), nullable=True))


def downgrade():
    # Remove the columns if we need to roll back
    op.drop_column('opportunities', 'work_time')
    op.drop_column('opportunities', 'started_at') 