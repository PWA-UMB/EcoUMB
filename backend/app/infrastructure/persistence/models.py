"""Modelo de datos completo del SAD §5 (10 tablas).

Tipos portables: ``Uuid`` genérico, ``JSON`` con variante ``JSONB`` e ``INET`` en PostgreSQL.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.roles import Role
from app.infrastructure.persistence.base import Base

JSON_TYPE = JSON().with_variant(postgresql.JSONB(), "postgresql")
IP_TYPE = String(45).with_variant(postgresql.INET(), "postgresql")
BIGINT_PK = BigInteger().with_variant(Integer(), "sqlite")


class ConfidenceBand(enum.StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RedemptionStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DELIVERED = "delivered"
    REJECTED = "rejected"


def _enum(enum_class: type[enum.StrEnum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda e: [m.value for m in e])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(
        _enum(Role, "user_role"), nullable=False, default=Role.USER, server_default=Role.USER.value
    )
    total_points: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class WasteCategoryModel(TimestampMixin, Base):
    """Las 3 categorías normativas de la Resolución 2184 de 2019."""

    __tablename__ = "waste_categories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    bag_color: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    educational_text: Mapped[str] = mapped_column(Text, nullable=False)


class WasteItemModel(TimestampMixin, Base):
    """Catálogo de objetos = clases de salida del modelo de IA."""

    __tablename__ = "waste_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    class_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("waste_categories.id"), nullable=False, index=True
    )
    icon_url: Mapped[str | None] = mapped_column(String(255))
    short_message: Mapped[str] = mapped_column(Text, nullable=False)
    disposal_tip: Mapped[str] = mapped_column(Text, nullable=False)
    points_value: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10, server_default="10"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class MlModelVersionModel(TimestampMixin, Base):
    __tablename__ = "ml_model_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    precision_per_class: Mapped[Any | None] = mapped_column(JSON_TYPE)
    recall_per_class: Mapped[Any | None] = mapped_column(JSON_TYPE)
    f1_per_class: Mapped[Any | None] = mapped_column(JSON_TYPE)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class ClassificationModel(TimestampMixin, Base):
    __tablename__ = "classifications"
    __table_args__ = (
        Index("ix_classifications_user_created", "user_id", "created_at"),
        Index("ix_classifications_image_phash", "image_phash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    ai_predicted_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("waste_items.id"))
    ai_predicted_category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("waste_categories.id")
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    top3_predictions: Mapped[Any | None] = mapped_column(JSON_TYPE)
    final_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("waste_items.id"))
    final_category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("waste_categories.id"))
    was_corrected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    confidence_band: Mapped[ConfidenceBand | None] = mapped_column(
        _enum(ConfidenceBand, "confidence_band")
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ml_model_versions.id"))
    points_awarded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    device_fingerprint: Mapped[str | None] = mapped_column(String(64))
    image_phash: Mapped[str | None] = mapped_column(String(64))


class RewardModel(TimestampMixin, Base):
    __tablename__ = "rewards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    points_required: Mapped[int] = mapped_column(Integer, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class RewardRedemptionModel(TimestampMixin, Base):
    __tablename__ = "reward_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reward_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rewards.id"), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RedemptionStatus] = mapped_column(
        _enum(RedemptionStatus, "redemption_status"),
        nullable=False,
        default=RedemptionStatus.PENDING,
        server_default=RedemptionStatus.PENDING.value,
    )
    redemption_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)


class AchievementModel(TimestampMixin, Base):
    __tablename__ = "achievements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(255))
    points_bonus: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    condition_json: Mapped[Any | None] = mapped_column(JSON_TYPE)


class UserAchievementModel(Base):
    __tablename__ = "user_achievements"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    achievement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("achievements.id"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditLogModel(Base):
    """RNF-07. Solo inserciones; sin ``updated_at``."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    ip_address: Mapped[str | None] = mapped_column(IP_TYPE)
    user_agent: Mapped[str | None] = mapped_column(Text)
    # "metadata" está reservado por SQLAlchemy Declarative: el atributo se llama distinto.
    extra_metadata: Mapped[Any | None] = mapped_column("metadata", JSON_TYPE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
