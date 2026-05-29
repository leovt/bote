"""add anonymous tables and challenges

Revision ID: a1f2d3c4b5e6
Revises: 9f419b5e417e
Create Date: 2026-05-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1f2d3c4b5e6'
down_revision = '9f419b5e417e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('game_table',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('player1', sa.String(length=80), nullable=False),
        sa.Column('player2', sa.String(length=80), nullable=True),
        sa.Column('deck1', sa.JSON(), nullable=True),
        sa.Column('deck2', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('challenge',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenger', sa.String(length=80), nullable=False),
        sa.Column('target', sa.String(length=80), nullable=False),
        sa.Column('table_id', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['table_id'], ['game_table.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('challenge')
    op.drop_table('game_table')
