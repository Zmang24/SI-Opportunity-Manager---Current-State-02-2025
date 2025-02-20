"""Fix version number

Revision ID: 003
Revises: 002
Create Date: 2024-02-17 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade():
    # This is just a version fix, no actual schema changes
    pass

def downgrade():
    # This is just a version fix, no actual schema changes
    pass 