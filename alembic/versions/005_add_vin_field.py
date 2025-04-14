"""Add VIN field to opportunities table

Revision ID: 005
Revises: 004
Create Date: 2023-07-19 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # Add VIN column to opportunities table
    op.add_column('opportunities', sa.Column('vin', sa.String(), nullable=True))


def downgrade():
    # Remove VIN column from opportunities table
    op.drop_column('opportunities', 'vin') 