from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class HealthCheck(Base):
    """Audit record used by the /api/health diagnostic endpoint.

    Each invocation writes a new row (with a sample embedding vector) and
    the endpoint immediately reads the latest row back, proving read/write
    connectivity end-to-end (Next.js -> FastAPI -> Postgres/pgvector).
    """

    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    test_vector: Mapped[list[float]] = mapped_column(Vector(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
