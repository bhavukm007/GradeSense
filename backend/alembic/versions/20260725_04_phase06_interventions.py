"""Add persistent forecast recommendations, decisions, and outcomes.

Revision ID: 20260725_04
Revises: 20260725_03
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_04"
down_revision: str | None = "20260725_03"
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
        "forecast_recommendations",
        sa.Column("forecast_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("affected_variables", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("baseline_trajectory", sa.JSON(), nullable=False),
        sa.Column("intervention_trajectory", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("constraint_validation", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *common_columns(),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecast_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_recommendations_forecast_id", "forecast_recommendations", ["forecast_id"])
    op.create_index("ix_forecast_recommendations_state", "forecast_recommendations", ["state"])
    op.create_index("ix_forecast_recommendations_expires_at", "forecast_recommendations", ["expires_at"])
    op.create_table(
        "recommendation_decisions",
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("operator_action", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("modified_values", sa.JSON()),
        sa.Column("delay_duration_seconds", sa.Integer()),
        sa.Column("notes", sa.Text()),
        *common_columns(),
        sa.ForeignKeyConstraint(["recommendation_id"], ["forecast_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_decisions_recommendation_id", "recommendation_decisions", ["recommendation_id"])
    op.create_table(
        "recommendation_outcomes",
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("observations", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        *common_columns(),
        sa.ForeignKeyConstraint(["recommendation_id"], ["forecast_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id"),
    )
    op.create_index("ix_recommendation_outcomes_recommendation_id", "recommendation_outcomes", ["recommendation_id"])


def downgrade() -> None:
    op.drop_table("recommendation_outcomes")
    op.drop_table("recommendation_decisions")
    op.drop_table("forecast_recommendations")
