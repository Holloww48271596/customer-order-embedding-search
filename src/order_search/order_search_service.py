from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import APIError
from pydantic import BaseModel

from .infrai_embeddings import InfraiEmbedder
from .order_documents import CustomerOrderIndex, OrderDocument, SearchHit, SearchRequest


class IndexRequest(BaseModel):
    documents: list[OrderDocument]


class IndexResult(BaseModel):
    indexed: int


@lru_cache
def get_index() -> CustomerOrderIndex:
    return CustomerOrderIndex(InfraiEmbedder())


app = FastAPI(title="Customer order search")


@app.exception_handler(APIError)
async def surface_infrai_error(_request: Request, error: APIError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code or 502, content={"detail": error.message})


@app.post("/documents", response_model=IndexResult)
def index_documents(request: IndexRequest) -> IndexResult:
    return IndexResult(indexed=get_index().add(request.documents))


@app.post("/search", response_model=list[SearchHit])
def search_documents(request: SearchRequest) -> list[SearchHit]:
    return get_index().search(request)
