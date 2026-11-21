import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status

from app.application.classification import use_cases
from app.interfaces.api.deps import (
    CatalogDep,
    ClassificationRepositoryDep,
    ClassifierDep,
    CurrentUser,
    StorageDep,
    classify_rate_limit,
)
from app.interfaces.schemas.classification import (
    ClassificationResponse,
    FeedbackRequest,
    HistoryResponse,
    to_response,
)

router = APIRouter(prefix="/classifications", tags=["classifications"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClassificationResponse,
    dependencies=[Depends(classify_rate_limit)],
)
def create_classification(
    request: Request,
    image: Annotated[
        UploadFile, File(description="Foto del residuo (JPEG, PNG o WebP, máx. 5 MB)")
    ],
    user: CurrentUser,
    catalog: CatalogDep,
    classifier: ClassifierDep,
    storage: StorageDep,
    repo: ClassificationRepositoryDep,
) -> ClassificationResponse:
    """RF-09 a RF-16. Clasifica la foto (modelo **simulado**) y la registra en el historial."""
    max_bytes = request.app.state.settings.max_image_bytes
    data = image.file.read(max_bytes + 1)  # un byte de más basta para saber que se pasó del límite
    record = use_cases.classify_waste(
        catalog, classifier, storage, repo, user_id=user.id, image=data, max_bytes=max_bytes
    )
    return to_response(record)


@router.get("/me", response_model=HistoryResponse)
def my_history(
    user: CurrentUser,
    repo: ClassificationRepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HistoryResponse:
    """RF-16, RF-17. Clasificaciones del usuario, de la más reciente a la más antigua."""
    records, total = use_cases.list_history(repo, user.id, limit=limit, offset=offset)
    return HistoryResponse(
        items=[to_response(r) for r in records], total=total, limit=limit, offset=offset
    )


@router.put("/{classification_id}/feedback", response_model=ClassificationResponse)
def give_feedback(
    classification_id: uuid.UUID,
    body: FeedbackRequest,
    user: CurrentUser,
    catalog: CatalogDep,
    repo: ClassificationRepositoryDep,
) -> ClassificationResponse:
    """RF-29, RF-30. Confirma o corrige lo que era el residuo; la última respuesta prevalece."""
    record = use_cases.give_feedback(
        catalog,
        repo,
        user_id=user.id,
        classification_id=classification_id,
        item_code=body.item_code,
    )
    return to_response(record)


@router.get("/{classification_id}/image", response_class=Response)
def classification_image(
    classification_id: uuid.UUID,
    user: CurrentUser,
    repo: ClassificationRepositoryDep,
    storage: StorageDep,
) -> Response:
    """La foto guardada. Solo la ve su dueño; para cualquier otro es un 404."""
    data, content_type = use_cases.get_classification_image(
        repo, storage, user.id, classification_id
    )
    return Response(
        content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"}
    )
