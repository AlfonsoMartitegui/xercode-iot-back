"""expand_tenant_fields

Revision ID: f03b39532183
Revises: d53bd0e2d398
Create Date: 2026-04-22 20:10:21.842317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f03b39532183'
down_revision: Union[str, Sequence[str], None] = 'd53bd0e2d398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tenants', sa.Column('address', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('redirect_url', sa.String(length=255), nullable=True))
    op.add_column('tenants', sa.Column('beaver_base_url', sa.String(length=255), nullable=True))
    op.add_column(
        'tenants',
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(),
            server_default=sa.text('current_timestamp()'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenants', 'updated_at')
    op.drop_column('tenants', 'beaver_base_url')
    op.drop_column('tenants', 'redirect_url')
    op.drop_column('tenants', 'address')
