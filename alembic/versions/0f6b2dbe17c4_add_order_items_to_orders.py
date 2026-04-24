"""Add order_items column to orders."""
from alembic import op
import sqlalchemy as sa

revision = '0f6b2dbe17c4'
down_revision = '6d1a9bb4f2c1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('order_items', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('orders', 'order_items')
