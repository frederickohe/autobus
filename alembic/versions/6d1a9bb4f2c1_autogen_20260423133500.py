"""Make order customer identity independent from users table."""
from alembic import op
import sqlalchemy as sa

revision = '6d1a9bb4f2c1'
down_revision = 'a8fe23c6fe7a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('orders_customer_id_fkey', 'orders', type_='foreignkey')
    op.alter_column('orders', 'customer_id', existing_type=sa.String(length=20), nullable=True)
    op.add_column('orders', sa.Column('customer_name', sa.String(length=150), nullable=True))
    op.add_column('orders', sa.Column('customer_phone', sa.String(length=30), nullable=True))
    op.add_column('orders', sa.Column('customer_location', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('orders', 'customer_location')
    op.drop_column('orders', 'customer_phone')
    op.drop_column('orders', 'customer_name')
    op.alter_column('orders', 'customer_id', existing_type=sa.String(length=20), nullable=False)
    op.create_foreign_key('orders_customer_id_fkey', 'orders', 'users', ['customer_id'], ['id'])
