"""Add sequential forecast persistence.

Revision ID: 20260725_03
Revises: 20260725_02
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260725_03"
down_revision: str | None = "20260725_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common_columns() -> list[sa.Column]:
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
        "forecast_history",
        sa.Column("transition_id", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=96), nullable=False),
        sa.Column("request_data", sa.JSON(), nullable=False),
        sa.Column("trajectory", sa.JSON(), nullable=False),
        sa.Column("specification", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("top_influencing_variables", sa.JSON(), nullable=False),
        *common_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_history_transition_id", "forecast_history", ["transition_id"])
    op.create_index("ix_forecast_history_model_version", "forecast_history", ["model_version"])
    op.create_table(
        "forecast_crossing_events",
        sa.Column("forecast_id", sa.Uuid(), nullable=False),
        sa.Column("crossing_step", sa.Integer(), nullable=False),
        sa.Column("crossing_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        *common_columns(),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecast_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_crossing_events_forecast_id", "forecast_crossing_events", ["forecast_id"])
    op.create_table(
        "intervention_simulations",
        sa.Column("forecast_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("baseline_trajectory", sa.JSON(), nullable=False),
        sa.Column("intervention_trajectory", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        *common_columns(),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecast_history.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id"),
    )
    op.create_index("ix_intervention_simulations_forecast_id", "intervention_simulations", ["forecast_id"])
    op.create_index("ix_intervention_simulations_recommendation_id", "intervention_simulations", ["recommendation_id"])


def downgrade() -> None:
    op.drop_table("intervention_simulations")
    op.drop_table("forecast_crossing_events")
    op.drop_table("forecast_history")
