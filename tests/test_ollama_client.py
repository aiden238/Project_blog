from __future__ import annotations

import httpx
import pytest

from src.llm.ollama_client import OllamaClient, OllamaClientError


def test_ollama_client_parses_completion_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            json={
                "response": "draft body",
                "model": "gemma3:12b",
                "prompt_eval_count": 12,
                "eval_count": 34,
            },
        )

    client = httpx.Client(
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(handler),
    )
    ollama = OllamaClient(client=client, max_retries=1)

    completion = ollama.generate("hello")

    assert completion.text == "draft body"
    assert completion.prompt_tokens == 12
    assert completion.completion_tokens == 34


def test_ollama_client_retries_then_raises() -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(500, request=request, json={"error": "boom"})

    client = httpx.Client(
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(handler),
    )
    ollama = OllamaClient(client=client, max_retries=3, sleep_fn=lambda _seconds: None)

    with pytest.raises(OllamaClientError):
        ollama.generate("hello")

    assert attempts["count"] == 3
