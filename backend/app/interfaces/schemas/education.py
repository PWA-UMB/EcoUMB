from pydantic import BaseModel

from app.domain.entities.education import EducationContent


class NormativeOut(BaseModel):
    title: str
    summary: str
    note: str


class BagItemOut(BaseModel):
    code: str
    display_name: str
    disposal_tip: str


class BagOut(BaseModel):
    category: str
    bag_color: str
    description: str
    educational_text: str
    items: list[BagItemOut]


class PracticeOut(BaseModel):
    title: str
    text: str


class EducationResponse(BaseModel):
    normative: NormativeOut
    bags: list[BagOut]
    practices: list[PracticeOut]


def to_response(content: EducationContent) -> EducationResponse:
    return EducationResponse(
        normative=NormativeOut(
            title=content.normative.title,
            summary=content.normative.summary,
            note=content.normative.note,
        ),
        bags=[
            BagOut(
                category=bag.category.code,
                bag_color=bag.category.bag_color,
                description=bag.category.description,
                educational_text=bag.category.educational_text,
                items=[
                    BagItemOut(
                        code=i.code, display_name=i.display_name, disposal_tip=i.disposal_tip
                    )
                    for i in bag.items
                ],
            )
            for bag in content.bags
        ],
        practices=[PracticeOut(title=p.title, text=p.text) for p in content.practices],
    )
