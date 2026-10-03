"""GPT-6 Astra adapter for treasury reasoning.

The model receives only validated, minimized treasury facts. It cannot post payments,
change limits, value derivatives, or approve transactions. Deterministic engines remain
the source of financial numbers and the policy engine remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class AstraRequest:
    task: str
    system_instruction: str
    validated_context: dict[str, Any]
    max_output_tokens: int = 450


@dataclass(frozen=True)
class AstraResponse:
    enabled: bool
    model: str
    text: str | None
    response_id: str | None = None
    error: str | None = None


class AstraTreasuryReasoner:
    """Small Responses API client with an explicit disabled mode for local development."""

    def __init__(self) -> None:
        self.model = settings.ai_model
        self.endpoint = settings.openai_base_url.rstrip("/") + "/responses"

    @property
    def enabled(self) -> bool:
        return bool(settings.openai_api_key and settings.ai_enabled)

    async def explain(self, request: AstraRequest) -> AstraResponse:
        if not self.enabled:
            return AstraResponse(
                enabled=False,
                model=self.model,
                text=None,
                error="Astra is configured but disabled until OPENAI_API_KEY and AI_ENABLED=true are supplied.",
            )

        payload = {
            "model": self.model,
            "instructions": request.system_instruction,
            "input": [
                {
                    "role": "user",
                    "content": (
                        f"Task: {request.task}\n\n"
                        f"Validated treasury context:\n{request.validated_context}\n\n"
                        "Use only the supplied facts. Do not invent values. "
                        "Distinguish observed facts, scenario assumptions, and recommendations. "
                        "Keep the answer concise and decision-useful."
                    ),
                }
            ],
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(self.endpoint, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except Exception as exc:  # network/provider failure must never break treasury calculations
            return AstraResponse(enabled=True, model=self.model, text=None, error=str(exc))

        chunks: list[str] = []
        for item in body.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    chunks.append(content["text"])
        return AstraResponse(
            enabled=True,
            model=body.get("model", self.model),
            text="\n".join(chunks).strip() or None,
            response_id=body.get("id"),
            error=None if chunks else "Provider returned no output_text content.",
        )
