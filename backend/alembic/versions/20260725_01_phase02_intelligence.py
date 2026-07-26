"""Add Phase 02 intelligence persistence.

Revision ID: 20260725_01
Revises:
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_metadata",
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("model_type", sa.String(length=128), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_records", sa.Integer(), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_metadata")),
        sa.UniqueConstraint("version", name=op.f("uq_model_metadata_version")),
    )
    op.create_index(
        op.f("ix_model_metadata_version"), "model_metadata", ["version"], unique=False
    )
    op.create_table(
        "prediction_history",
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("off_spec_probability", sa.Float(), nullable=False),
        sa.Column("stabilization_time", sa.Float(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prediction_history")),
    )
    op.create_index(
        op.f("ix_prediction_history_model_version"),
        "prediction_history",
        ["model_version"],
        unique=False,
    )
    op.create_table(
        "recommendation_history",
        sa.Column("prediction_id", sa.Uuid(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["prediction_history.id"],
            name=op.f("fk_recommendation_history_prediction_id_prediction_history"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_history")),
    )
    op.create_index(
        op.f("ix_recommendation_history_prediction_id"),
        "recommendation_history",
        ["prediction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recommendation_history_prediction_id"),
        table_name="recommendation_history",
    )
    op.drop_table("recommendation_history")
    op.drop_index(
        op.f("ix_prediction_history_model_version"), table_name="prediction_history"
    )
    op.drop_table("prediction_history")
    op.drop_index(op.f("ix_model_metadata_version"), table_name="model_metadata")
    op.drop_table("model_metadata")
