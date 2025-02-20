"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-03-14

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('pin_hash', sa.String(255), nullable=False),
        sa.Column('email', sa.String(100)),
        sa.Column('role', sa.String(20), server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('make', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('is_custom', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create opportunities table
    op.create_table(
        'opportunities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('status', sa.String(50), server_default='new'),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('assigned_to', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('response_time', sa.Interval()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create adas_systems table
    op.create_table(
        'adas_systems',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(20), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Create opportunity_systems table
    op.create_table(
        'opportunity_systems',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id', ondelete='CASCADE')),
        sa.Column('system_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('adas_systems.id', ondelete='CASCADE')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('opportunity_id', sa.Integer(), sa.ForeignKey('opportunities.id')),
        sa.Column('file_path', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('attachments')
    op.drop_table('opportunity_systems')
    op.drop_table('adas_systems')
    op.drop_table('opportunities')
    op.drop_table('vehicles')
    op.drop_table('users') 