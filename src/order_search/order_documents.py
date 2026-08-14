from __future__ import annotations

from enum import StrEnum
from math import sqrt
from typing import Protocol

from pydantic import BaseModel, Field


class OrderStage(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    UPDATE = "update"


class OrderDocument(BaseModel):
    document_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    stage: OrderStage
    text: str = Field(min_length=1)


class SearchRequest(BaseModel):
    customer_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    stages: list[OrderStage] = Field(default_factory=list)
    limit: int = Field(default=3, ge=1, le=20)


class SearchHit(BaseModel):
    document: OrderDocument
    score: float


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for each input string."""


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    denominator = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return numerator / denominator if denominator else 0.0


class CustomerOrderIndex:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._documents: dict[str, OrderDocument] = {}
        self._embeddings: dict[str, list[float]] = {}

    def add(self, documents: list[OrderDocument]) -> int:
        vectors = self._embedder.embed([document.text for document in documents])
        if len(vectors) != len(documents):
            raise ValueError("Embedding response count did not match the document count")
        for document, vector in zip(documents, vectors, strict=True):
            self._documents[document.document_id] = document
            self._embeddings[document.document_id] = vector
        return len(documents)

    def search(self, request: SearchRequest) -> list[SearchHit]:
        query_vector = self._embedder.embed([request.query])[0]
        allowed_stages = set(request.stages)
        candidates = (
            document
            for document in self._documents.values()
            if document.customer_id == request.customer_id
            and (not allowed_stages or document.stage in allowed_stages)
        )
        hits = [
            SearchHit(
                document=document,
                score=_cosine(query_vector, self._embeddings[document.document_id]),
            )
            for document in candidates
        ]
        return sorted(hits, key=lambda hit: (-hit.score, hit.document.document_id))[: request.limit]
