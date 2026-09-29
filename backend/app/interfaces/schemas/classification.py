import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.confidence import ConfidenceBand
from app.domain.entities.classification import Classification, WasteItem

IMAGE_URL_TEMPLATE = "/api/v1/classifications/{id}/image"


class ItemOut(BaseModel):
    code: str
    display_name: str


class CategoryOut(BaseModel):
    code: str
    bag_color: str


class CandidateOut(BaseModel):
    code: str
    display_name: str
    bag_color: str
    confidence: float


class FeedbackOut(BaseModel):
    item: ItemOut
    category: CategoryOut
    was_corrected: bool


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_code: str = Field(min_length=1, max_length=50)


class ClassificationResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    simulated: bool
    model_version: str | None
    confidence: float
    confidence_band: ConfidenceBand
    item: ItemOut
    category: CategoryOut
    message: str
    tip: str
    points_awarded: int
    top3: list[CandidateOut]
    image_url: str
    feedback: FeedbackOut | None


class HistoryResponse(BaseModel):
    items: list[ClassificationResponse]
    total: int
    limit: int
    offset: int


def _category(item: WasteItem) -> CategoryOut:
    return CategoryOut(code=item.category_code, bag_color=item.bag_color)


def _feedback(record: Classification) -> FeedbackOut | None:
    if record.feedback is None:
        return None
    item = record.feedback.item
    return FeedbackOut(
        item=ItemOut(code=item.code, display_name=item.display_name),
        category=_category(item),
        was_corrected=record.feedback.was_corrected,
    )


def to_response(record: Classification) -> ClassificationResponse:
    return ClassificationResponse(
        id=record.id,
        created_at=record.created_at,
        simulated=record.simulated,
        model_version=record.model_version,
        confidence=record.confidence,
        confidence_band=record.band,
        item=ItemOut(code=record.item.code, display_name=record.item.display_name),
        category=_category(record.item),
        message=record.item.short_message,
        tip=record.item.disposal_tip,
        points_awarded=record.points_awarded,
        top3=[
            CandidateOut(
                code=c.item.code,
                display_name=c.item.display_name,
                bag_color=c.item.bag_color,
                confidence=c.confidence,
            )
            for c in record.top3
        ],
        image_url=IMAGE_URL_TEMPLATE.format(id=record.id),
        feedback=_feedback(record),
    )
