from fastapi import APIRouter

from app.application.education.use_cases import get_education
from app.interfaces.api.deps import CatalogDep, CategoryCatalogDep, CurrentUser
from app.interfaces.schemas.education import EducationResponse, to_response

router = APIRouter(prefix="/education", tags=["education"])


@router.get("", response_model=EducationResponse)
def read_education(
    _: CurrentUser, catalog: CatalogDep, categories: CategoryCatalogDep
) -> EducationResponse:
    """RF-26, RF-27, RF-28. Guía: normativa, bolsas con sus objetos y buenas prácticas."""
    return to_response(get_education(catalog, categories))
