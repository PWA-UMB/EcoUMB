"""Esquema inicial: las 10 tablas del SAD, sección 5.

Revision ID: 0001
Revises:
Create Date: 2026-09-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
IP_TYPE = sa.String(45).with_variant(postgresql.INET(), "postgresql")
BIGINT_PK = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

USER_ROLE = ("user", "cleaner", "admin")
CONFIDENCE_BAND = ("high", "medium", "low")
REDEMPTION_STATUS = ("pending", "approved", "delivered", "rejected")
ENUM_TYPES = ("user_role", "confidence_band", "redemption_status")


def _timestamps() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120)),
        sa.Column("role", sa.Enum(*USER_ROLE, name="user_role"), server_default="user", nullable=False),
        sa.Column("total_points", sa.Integer(), server_default="0", nullable=False),
        sa.Column("level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "waste_categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("bag_color", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("educational_text", sa.Text(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "waste_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("waste_categories.id"), nullable=False),
        sa.Column("icon_url", sa.String(255)),
        sa.Column("short_message", sa.Text(), nullable=False),
        sa.Column("disposal_tip", sa.Text(), nullable=False),
        sa.Column("points_value", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("class_id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_waste_items_category_id", "waste_items", ["category_id"])

    op.create_table(
        "ml_model_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("accuracy", sa.Numeric(5, 4)),
        sa.Column("precision_per_class", JSON_TYPE),
        sa.Column("recall_per_class", JSON_TYPE),
        sa.Column("f1_per_class", JSON_TYPE),
        sa.Column("trained_at", sa.DateTime(timezone=True)),
        sa.Column("model_path", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "classifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("ai_predicted_item_id", sa.Uuid(), sa.ForeignKey("waste_items.id")),
        sa.Column("ai_predicted_category_id", sa.Uuid(), sa.ForeignKey("waste_categories.id")),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("top3_predictions", JSON_TYPE),
        sa.Column("final_item_id", sa.Uuid(), sa.ForeignKey("waste_items.id")),
        sa.Column("final_category_id", sa.Uuid(), sa.ForeignKey("waste_categories.id")),
        sa.Column("was_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("confidence_band", sa.Enum(*CONFIDENCE_BAND, name="confidence_band")),
        sa.Column("model_version_id", sa.Uuid(), sa.ForeignKey("ml_model_versions.id")),
        sa.Column("points_awarded", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("device_fingerprint", sa.String(64)),
        sa.Column("image_phash", sa.String(64)),
        *_timestamps(),
    )
    op.create_index("ix_classifications_user_created", "classifications", ["user_id", "created_at"])
    op.create_index("ix_classifications_image_phash", "classifications", ["image_phash"])

    op.create_table(
        "rewards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("points_required", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
    )

    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reward_id", sa.Uuid(), sa.ForeignKey("rewards.id"), nullable=False),
        sa.Column("points_spent", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*REDEMPTION_STATUS, name="redemption_status"),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("redemption_code", sa.String(20), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("redemption_code"),
    )
    op.create_index("ix_reward_redemptions_user_id", "reward_redemptions", ["user_id"])

    op.create_table(
        "achievements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("icon", sa.String(255)),
        sa.Column("points_bonus", sa.Integer(), server_default="0", nullable=False),
        sa.Column("condition_json", JSON_TYPE),
        *_timestamps(),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "user_achievements",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("achievement_id", sa.Uuid(), sa.ForeignKey("achievements.id"), primary_key=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", BIGINT_PK, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(50)),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("ip_address", IP_TYPE),
        sa.Column("user_agent", sa.Text()),
        sa.Column("metadata", JSON_TYPE),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_index("ix_reward_redemptions_user_id", table_name="reward_redemptions")
    op.drop_table("reward_redemptions")
    op.drop_table("rewards")
    op.drop_index("ix_classifications_image_phash", table_name="classifications")
    op.drop_index("ix_classifications_user_created", table_name="classifications")
    op.drop_table("classifications")
    op.drop_table("ml_model_versions")
    op.drop_index("ix_waste_items_category_id", table_name="waste_items")
    op.drop_table("waste_items")
    op.drop_table("waste_categories")
    op.drop_table("users")

    # PostgreSQL no elimina los tipos ENUM al borrar las tablas que los usan.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in ENUM_TYPES:
            postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
