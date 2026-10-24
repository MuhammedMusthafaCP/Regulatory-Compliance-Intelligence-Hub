from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.system import Base


class Document(Base):
    """A regulatory source text (e.g. GDPR) that chunks are cut from."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    celex: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(5), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[str] = mapped_column(String(50), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_max_words: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    """One retrieval unit (article paragraph/point/definition or recital).

    Embeddings are added in a later migration, once the model (and its real
    dimension) is chosen. ``text_sha256`` lets that step detect changed text.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # article | recital
    split_reason: Mapped[str] = mapped_column(String(20), nullable=False)
    citation: Mapped[str] = mapped_column(String(100), nullable=False)

    chapter: Mapped[str | None] = mapped_column(String(10))
    chapter_title: Mapped[str | None] = mapped_column(String(255))
    section: Mapped[int | None] = mapped_column(Integer)
    section_title: Mapped[str | None] = mapped_column(String(255))
    article_number: Mapped[int | None] = mapped_column(Integer)
    article_title: Mapped[str | None] = mapped_column(String(255))
    article_id: Mapped[str | None] = mapped_column(String(50))
    paragraph: Mapped[str | None] = mapped_column(String(10))
    paragraph_index: Mapped[int | None] = mapped_column(Integer)
    point: Mapped[str | None] = mapped_column(String(20))
    recital_number: Mapped[int | None] = mapped_column(Integer)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    lead_in: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    source_anchor: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    cross_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    footnote_refs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_ordinal", "document_id", "ordinal"),
        Index("ix_chunks_document_article", "document_id", "article_number"),
        Index("ix_chunks_type", "type"),
    )
