"""Explicit initial schema. Do not use create_all in the application startup."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("saga_id", sa.String(36), nullable=False, unique=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "quote_id", sa.String(36), sa.ForeignKey("quotes.id"), nullable=False, unique=True
        ),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "inbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("digest", sa.String(64), nullable=False),
    )
    op.create_table(
        "outbox",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.String(36), nullable=False, unique=True),
        sa.Column("saga_id", sa.String(36), nullable=False),
        sa.Column("message", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_outbox_saga_id", "outbox", ["saga_id"])
    op.create_index("ix_outbox_published", "outbox", ["published"])
    op.create_table(
        "provider_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_provider_operations_status", "provider_operations", ["status"])
    op.create_index("ix_provider_operations_available_at", "provider_operations", ["available_at"])


def downgrade():
    for name in ["provider_operations", "outbox", "inbox", "payments", "quotes"]:
        op.drop_table(name)
