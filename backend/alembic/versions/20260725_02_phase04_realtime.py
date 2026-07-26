"""Add Phase 04 real-time monitoring persistence.

Revision ID: 20260725_02
Revises: 20260725_01
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260725_02"
down_revision: str | None = "20260725_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "alert_history",
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_variables", sa.JSON(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("prediction_id", sa.Uuid()),
        *timestamps(),
        sa.ForeignKeyConstraint(["prediction_id"], ["prediction_history.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_history_severity", "alert_history", ["severity"])
    op.create_index("ix_alert_history_prediction_id", "alert_history", ["prediction_id"])
    op.create_table(
        "operator_feedback",
        sa.Column("prediction_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text()),
        *timestamps(),
        sa.ForeignKeyConstraint(["prediction_id"], ["prediction_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operator_feedback_prediction_id", "operator_feedback", ["prediction_id"])
    op.create_table(
        "rolling_metric_snapshots",
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rolling_metric_snapshots_window", "rolling_metric_snapshots", ["window"])
    op.create_table(
        "streaming_sessions",
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("streaming_sessions")
    op.drop_index("ix_rolling_metric_snapshots_window", "rolling_metric_snapshots")
    op.drop_table("rolling_metric_snapshots")
    op.drop_index("ix_operator_feedback_prediction_id", "operator_feedback")
    op.drop_table("operator_feedback")
    op.drop_index("ix_alert_history_prediction_id", "alert_history")
    op.drop_index("ix_alert_history_severity", "alert_history")
    op.drop_table("alert_history")
