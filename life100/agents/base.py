"""Gemini API client wrapper for the runtime AI agents. SRS §20.

Google Gemini (Flash, free tier) instead of the originally-specced Anthropic
API — see SCOPE.md. The `google-genai` import is deferred so importing this
module never requires the SDK/network/API key to be present; tests inject a
mock in place of `GeminiAgentClient` entirely (see tests/test_agents.py),
so no live API call happens during `pytest` (protects the free-tier quota).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.6-flash"


class GeminiClientError(Exception):
    pass


class GeminiAgentClient:
    """Structured-output client: every call asks Gemini to return JSON
    matching a schema, so the caller (an agent module) gets a dict back
    that a validator can check as data — never free text trusted as-is."""

    def __init__(self, api_key: str | None = None, model: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        self.max_retries = max_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai  # deferred import, see module docstring

            if not self.api_key:
                raise GeminiClientError("GEMINI_API_KEY is not set")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any],
        system_instruction: str | None = None,
    ) -> dict[str, Any]:
        """Call Gemini and return the parsed JSON response.

        Retries with exponential backoff on rate-limit errors — the Gemini
        free tier has low per-minute quotas, and this submission's demo
        should degrade to "try again in a moment" rather than crash.
        """
        from google.genai import types  # deferred import, see module docstring

        client = self._get_client()
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = client.models.generate_content(model=self.model, contents=prompt, config=config)
                return json.loads(response.text)
            except Exception as exc:  # noqa: BLE001 — broad on purpose, see retry/raise below
                last_error = exc
                is_rate_limited = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
                if is_rate_limited and attempt < self.max_retries - 1:
                    backoff_seconds = 2**attempt
                    logger.warning("Gemini rate-limited (attempt %s), backing off %ss", attempt + 1, backoff_seconds)
                    time.sleep(backoff_seconds)
                    continue
                raise GeminiClientError(f"Gemini call failed: {exc}") from exc

        raise GeminiClientError(f"Gemini call failed after {self.max_retries} attempts: {last_error}")
