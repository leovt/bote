"""empty message

Revision ID: 9f419b5e417e
Revises: 61cd4454b960
Create Date: 2020-04-09 01:16:24.863378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f419b5e417e'
down_revision = '61cd4454b960'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('deck', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public', sa.Boolean(), nullable=False, server_default="0"))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('deck', schema=None) as batch_op:
        batch_op.drop_column('public')

    # ### end Alembic commands ###
