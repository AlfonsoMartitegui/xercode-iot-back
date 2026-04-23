"""beaver_model_alignment

Revision ID: 6c90d57d8e3f
Revises: f03b39532183
Create Date: 2026-04-23 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c90d57d8e3f"
down_revision: Union[str, Sequence[str], None] = "f03b39532183"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("current_timestamp()"),
            nullable=True,
        ),
    )
    op.alter_column("users", "email", existing_type=sa.String(length=150), nullable=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.add_column("tenants", sa.Column("beaver_admin_username", sa.String(length=150), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("beaver_admin_password_encrypted", sa.String(length=512), nullable=True),
    )

    op.add_column("user_tenants", sa.Column("beaver_role_id", sa.String(length=100), nullable=True))
    op.add_column(
        "user_tenants",
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("current_timestamp()"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_tenants", "updated_at")
    op.drop_column("user_tenants", "beaver_role_id")

    op.drop_column("tenants", "beaver_admin_password_encrypted")
    op.drop_column("tenants", "beaver_admin_username")

    op.drop_index("ix_users_email", table_name="users")
    op.alter_column("users", "email", existing_type=sa.String(length=150), nullable=True)
    op.drop_column("users", "updated_at")
