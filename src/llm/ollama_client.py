from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from src.config import settings


class OllamaClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class OllamaCompletion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    wall_time_sec: float


def create_ollama_http_client(base_url: str | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=base_url or settings.ollama_base_url,
        timeout=settings.ollama_timeout_sec,
    )


class OllamaClient:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
        sleep_fn=time.sleep,
    ) -> None:
        self.client = client or create_ollama_http_client()
        self.model = model or settings.ollama_model
        self.temperature = (
            settings.ollama_temperature if temperature is None else temperature
        )
        self.max_tokens = settings.ollama_max_tokens if max_tokens is None else max_tokens
        self.max_retries = (
            settings.ollama_max_retries if max_retries is None else max_retries
        )
        self.sleep_fn = sleep_fn

    def generate(self, prompt: str, *, system: str | None = None) -> OllamaCompletion:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            started_at = time.monotonic()
            try:
                response = self.client.post("/api/generate", json=payload)
                response.raise_for_status()
                body = response.json()
                wall_time_sec = time.monotonic() - started_at
                return OllamaCompletion(
                    text=str(body.get("response", "")).strip(),
                    model=str(body.get("model", self.model)),
                    prompt_tokens=int(body.get("prompt_eval_count") or 0),
                    completion_tokens=int(body.get("eval_count") or 0),
                    wall_time_sec=wall_time_sec,
                )
            except (httpx.HTTPError, ValueError) as error:
                last_error = error
                if attempt == self.max_retries - 1:
                    break
                self.sleep_fn(2**attempt)

        raise OllamaClientError(
            f"ollama generate failed after {self.max_retries} attempts: {last_error}"
        )
