"""Add model registry, immutable audit log, and runtime configuration.

Revision ID: 20260725_05
Revises: 20260725_04
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_05"
down_revision: str | None = "20260725_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "registered_models",
        sa.Column("version", sa.String(96), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("model_kind", sa.String(32), nullable=False),
        sa.Column("algorithm", sa.String(160), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_checksum", sa.String(64), nullable=False),
        sa.Column("feature_schema_checksum", sa.String(64), nullable=False),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("training_parameters", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        *common_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_kind", "version", name="uq_registered_models_kind_version"),
    )
    op.create_index("ix_registered_models_model_kind", "registered_models", ["model_kind"])
    op.create_index("ix_registered_models_status", "registered_models", ["status"])
    op.create_table(
        "audit_logs",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(160), nullable=False),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("entity", sa.String(96), nullable=False),
        sa.Column("entity_id", sa.String(96)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("request_id", sa.String(96)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("timestamp", "action", "entity", "entity_id", "request_id"):
        op.create_index(f"ix_audit_logs_{column}", "audit_logs", [column])
    op.create_table(
        "runtime_configuration",
        sa.Column("singleton_key", sa.String(32), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        *common_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("runtime_configuration")
    op.drop_table("audit_logs")
    op.drop_table("registered_models")
