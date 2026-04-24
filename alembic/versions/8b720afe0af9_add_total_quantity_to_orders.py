"""Add total_quantity column to orders."""
from alembic import op
import sqlalchemy as sa

revision = '8b720afe0af9'
down_revision = '0f6b2dbe17c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('total_quantity', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('orders', 'total_quantity')
