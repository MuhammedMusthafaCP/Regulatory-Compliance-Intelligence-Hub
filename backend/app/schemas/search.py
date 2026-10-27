from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="A plain-language compliance question.")

    @field_validator("question", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        # Strip before the length check so whitespace-only input counts as empty.
        return value.strip() if isinstance(value, str) else value


class Provision(BaseModel):
    """An operative provision (an article chunk): this is what an answer may cite."""

    role: Literal["operative"]
    citation: str = Field(examples=["Article 17(1)"])
    article: int
    article_title: str
    text: str
    score: float = Field(description="Reranker score. Relative only: scores of related clauses bunch near 1.0.")
    chunk_id: str
    source_url: str | None = None


class ContextRecital(BaseModel):
    """A recital shown as interpretive context. Never an answer on its own."""

    role: Literal["interpretive_context"]
    citation: str = Field(examples=["Recital 65"])
    text: str
    score: float
    relevance: float
    chunk_id: str
    source_url: str | None = None


class SearchResponse(BaseModel):
    question: str
    status: Literal["supported", "weak_evidence", "no_basis"]
    confidence: float = Field(description="Reranker score of the best provision (0-1). Not a probability.")
    note: str | None = None
    provisions: list[Provision]
    context: list[ContextRecital]
    took_ms: int


class SearchStatus(BaseModel):
    state: Literal["loading", "ready", "unavailable", "failed"]
    ready: bool


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    detail: ErrorDetail
