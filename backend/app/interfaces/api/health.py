from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness(request: Request) -> dict[str, str]:
    """El proceso responde."""
    return {"status": "ok", "version": request.app.version}


@router.get("/health/ready")
def readiness(request: Request) -> JSONResponse:
    """El proceso responde y la base de datos es alcanzable."""
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - cualquier fallo de BD significa "no listo"
        return JSONResponse({"status": "unavailable", "database": "error"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})
