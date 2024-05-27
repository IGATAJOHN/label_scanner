"""Initial migration

Revision ID: c43b36e8dbef
Revises: 
Create Date: 2024-05-26 21:09:54.723829

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c43b36e8dbef'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('label', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_name', sa.String(length=100), nullable=False, server_default='Unknown Product'))
        batch_op.add_column(sa.Column('brand', sa.String(length=100), nullable=False, server_default='Unknown Brand'))

def downgrade():
    with op.batch_alter_table('label', schema=None) as batch_op:
        batch_op.drop_column('product_name')
        batch_op.drop_column('brand')

