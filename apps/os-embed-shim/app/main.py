"""OpenAI-compatible /v1/embeddings adapter for OpenSearch ML Commons."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="os-embed-shim", version="0.1.0")


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _opensearch_settings() -> tuple[str, str | None, str | None, bool]:
    """Resolve OpenSearch URL and optional basic-auth from env.

    Supports either:
    - OPENSEARCH_URL + OPENSEARCH_USER + OPENSEARCH_PASSWORD
    - OPENSEARCH_CONNECTION_STRING (https://user:pass@host:port) from Aiven Runtime
    """
    verify = os.environ.get("OPENSEARCH_SSL_VERIFY", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    conn = os.environ.get("OPENSEARCH_CONNECTION_STRING", "").strip()
    if conn:
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(conn)
        user = parsed.username
        password = parsed.password
        # Rebuild without credentials for base_url
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        base = urlunparse((parsed.scheme or "https", netloc, "", "", "", "")).rstrip("/")
        return base, user, password, verify

    url = _env("OPENSEARCH_URL").rstrip("/")
    user = os.environ.get("OPENSEARCH_USER", "avnadmin")
    password = _env("OPENSEARCH_PASSWORD")
    return url, user, password, verify


def opensearch_client() -> httpx.Client:
    url, user, password, verify = _opensearch_settings()
    auth = (user, password) if user and password else None
    return httpx.Client(
        base_url=url,
        auth=auth,
        verify=verify,
        timeout=httpx.Timeout(120.0),
    )


class EmbeddingRequest(BaseModel):
    input: str | list[str]
    model: str | None = None
    encoding_format: str | None = None
    dimensions: int | None = None
    user: str | None = None


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class EmbeddingUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingData]
    model: str
    usage: EmbeddingUsage = Field(default_factory=EmbeddingUsage)


def _as_texts(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not value:
        raise HTTPException(status_code=400, detail="input must not be empty")
    return value


def _predict_embeddings(texts: list[str], model_id: str) -> list[list[float]]:
    with opensearch_client() as client:
        resp = client.post(
            f"/_plugins/_ml/_predict/text_embedding/{model_id}",
            json={
                "text_docs": texts,
                "return_number": True,
                "target_response": ["sentence_embedding"],
            },
        )
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "OpenSearch ML Commons predict failed",
                    "status_code": resp.status_code,
                    "body": resp.text[:2000],
                },
            )
        payload: dict[str, Any] = resp.json()

    results = payload.get("inference_results") or []
    embeddings: list[list[float]] = []
    for item in results:
        outputs = item.get("output") or []
        vec: list[float] | None = None
        for out in outputs:
            if out.get("name") == "sentence_embedding" or "data" in out:
                data = out.get("data")
                if isinstance(data, list):
                    vec = [float(x) for x in data]
                    break
        if vec is None:
            raise HTTPException(
                status_code=502,
                detail={"message": "No sentence_embedding in predict response", "item": item},
            )
        embeddings.append(vec)

    if len(embeddings) != len(texts):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Embedding count mismatch",
                "expected": len(texts),
                "got": len(embeddings),
            },
        )
    return embeddings


@app.get("/health")
@app.get("/health/live")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def list_models() -> dict[str, Any]:
    model_id = os.environ.get("OS_EMBED_MODEL_ID", "os-embed")
    return {
        "object": "list",
        "data": [
            {
                "id": "os-embed",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "aiven-opensearch-ml",
                "root": model_id,
            }
        ],
    }


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
def create_embeddings(body: EmbeddingRequest) -> EmbeddingResponse:
    model_id = os.environ.get("OS_EMBED_MODEL_ID")
    if not model_id:
        raise HTTPException(
            status_code=503,
            detail="OS_EMBED_MODEL_ID is not set; deploy an ML Commons model first",
        )
    texts = _as_texts(body.input)
    vectors = _predict_embeddings(texts, model_id)
    data = [
        EmbeddingData(embedding=vec, index=i) for i, vec in enumerate(vectors)
    ]
    # Approximate token usage; Gateway/Auto Ontology only need dimensions primarily.
    chars = sum(len(t) for t in texts)
    approx_tokens = max(1, chars // 4)
    return EmbeddingResponse(
        data=data,
        model=body.model or "os-embed",
        usage=EmbeddingUsage(prompt_tokens=approx_tokens, total_tokens=approx_tokens),
    )
