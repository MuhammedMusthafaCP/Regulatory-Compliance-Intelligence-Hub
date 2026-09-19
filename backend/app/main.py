from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.system import HealthCheck

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Phase 1 baseline API for the Regulatory & Compliance Intelligence "
        "Hub. Verifies end-to-end connectivity across Next.js, FastAPI, "
        "and Aiven PostgreSQL (pgvector)."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sample embedding used purely to prove pgvector read/write support.
SAMPLE_TEST_VECTOR = [0.1, 0.2, 0.3]


@app.get("/")
async def root() -> dict:
    return {"service": settings.PROJECT_NAME, "status": "online"}


@app.get(f"{settings.API_V1_PREFIX}/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    End-to-end diagnostic:
    1. Write a new HealthCheck row (with a sample pgvector embedding).
    2. Read the most recently created row back from the database.
    3. Return a JSON payload confirming DB read/write and vector support.
    """
    try:
        new_record = HealthCheck(status="ok", test_vector=SAMPLE_TEST_VECTOR)
        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)

        result = await db.execute(
            select(HealthCheck).order_by(HealthCheck.created_at.desc()).limit(1)
        )
        latest_record = result.scalar_one()

        return {
            "api_status": "healthy",
            "database_status": "connected",
            "write_verified": True,
            "read_verified": True,
            "vector_support_verified": True,
            "latest_record": {
                "id": latest_record.id,
                "status": latest_record.status,
                "test_vector": [float(x) for x in latest_record.test_vector],
                "created_at": latest_record.created_at.isoformat(),
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail=f"Database diagnostic failed: {exc}",
        ) from exc
