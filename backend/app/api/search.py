import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.schemas.search import ErrorResponse, SearchRequest, SearchResponse, SearchStatus
from app.services.search import SearchError, SearchService

logger = logging.getLogger("app.search")

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/search", tags=["search"])


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search


@router.get("/status", response_model=SearchStatus)
async def search_status(service: SearchService = Depends(get_search_service)) -> SearchStatus:
    """Whether the search engine has finished loading (it starts in the background)."""
    return SearchStatus(state=service.state, ready=service.ready)


@router.post(
    "",
    response_model=SearchResponse,
    responses={
        429: {"model": ErrorResponse, "description": "Too many searches queued"},
        500: {"model": ErrorResponse, "description": "Unexpected failure"},
        503: {"model": ErrorResponse, "description": "Engine starting up or unavailable"},
        504: {"model": ErrorResponse, "description": "Search timed out"},
    },
)
async def search(body: SearchRequest, service: SearchService = Depends(get_search_service)) -> SearchResponse:
    """Retrieve the GDPR provisions that support an answer, with recital context and an evidence status."""
    started = time.perf_counter()
    try:
        result = await service.search(body.question)
        return SearchResponse(**result, took_ms=round((time.perf_counter() - started) * 1000))
    except SearchError as exc:
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": exc.message}, headers=headers) from exc
    except Exception as exc:  # noqa: BLE001 - never leak internals to the client
        logger.exception("search failed")
        raise HTTPException(
            500, detail={"code": "search_failed", "message": "The search could not be completed. Please try again."}
        ) from exc
