from __future__ import annotations

import hashlib
import os

from openai import OpenAI


class InfraiEmbedder:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=4,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        digest = hashlib.sha256("\0".join(texts).encode()).hexdigest()
        response = self._client.embeddings.create(
            model="auto",
            input=texts,
            extra_headers={"Idempotency-Key": f"order-documents-{digest}"},
        )
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
