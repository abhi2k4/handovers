"""LLM provider adapter.

The LLM only extracts structure from free text and phrases prose. It never decides what is at risk,
what transfers, or who knows what; graph queries do that. Every caller has a deterministic fallback,
so the product works with `LLM_PROVIDER=none`.

Providers:
- vertex: Gemini on Vertex AI. Token from the GCE metadata server, or `gcloud auth print-access-token`
  locally (optionally for GCLOUD_ACCOUNT).
- anthropic: Claude via the Messages API (ANTHROPIC_API_KEY).
- groq: any Groq-hosted model via its OpenAI-compatible API (GROQ_API_KEY), e.g. openai/gpt-oss-120b.
"""

import asyncio
import json
import time
from typing import Any

import httpx

from core.config import Settings, get_settings
from core.logging import get_logger

log = get_logger("llm")

_METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
)


class LLMUnavailable(RuntimeError):
    """Raised when no provider is configured or a call fails; callers fall back to templates."""


class LLM:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._token: str | None = None
        self._token_expiry = 0.0
        self._client = httpx.AsyncClient(timeout=60)

    @property
    def enabled(self) -> bool:
        provider = self.settings.llm_provider
        if provider == "vertex":
            return bool(self.settings.gcp_project)
        if provider == "anthropic":
            return self.settings.anthropic_api_key is not None
        if provider == "groq":
            return self.settings.groq_api_key is not None
        return False

    @property
    def model(self) -> str:
        return self.settings.llm_model if self.enabled else "none"

    async def close(self) -> None:
        await self._client.aclose()

    async def json(self, system: str, prompt: str, schema: dict[str, Any]) -> Any:
        """Structured output: returns parsed JSON matching `schema` (an OpenAPI-style schema)."""
        if not self.enabled:
            raise LLMUnavailable("no LLM provider configured")
        try:
            if self.settings.llm_provider == "vertex":
                text = await self._vertex(system, prompt, schema)
            elif self.settings.llm_provider == "groq":
                text = await self._groq(system, prompt + _schema_hint(schema))
            else:
                text = await self._anthropic(system, prompt + _schema_hint(schema))
            return json.loads(_strip_fences(text))
        except LLMUnavailable:
            raise
        except Exception as exc:
            log.warning("llm_json_failed", error=f"{type(exc).__name__}: {exc}")
            raise LLMUnavailable(str(exc)) from exc

    async def text(self, system: str, prompt: str) -> str:
        if not self.enabled:
            raise LLMUnavailable("no LLM provider configured")
        try:
            if self.settings.llm_provider == "vertex":
                return (await self._vertex(system, prompt, None)).strip()
            if self.settings.llm_provider == "groq":
                return (await self._groq(system, prompt)).strip()
            return (await self._anthropic(system, prompt)).strip()
        except Exception as exc:
            log.warning("llm_text_failed", error=f"{type(exc).__name__}: {exc}")
            raise LLMUnavailable(str(exc)) from exc

    # ---- Vertex AI (Gemini) -------------------------------------------------------------------

    async def _vertex(self, system: str, prompt: str, schema: dict[str, Any] | None) -> str:
        s = self.settings
        host = (
            "aiplatform.googleapis.com"
            if s.gcp_location == "global"
            else f"{s.gcp_location}-aiplatform.googleapis.com"
        )
        url = (
            f"https://{host}/v1/projects/{s.gcp_project}/locations/{s.gcp_location}"
            f"/publishers/google/models/{s.llm_model}:generateContent"
        )
        config: dict[str, Any] = {"temperature": 0, "maxOutputTokens": 8192}
        if schema is not None:
            config["responseMimeType"] = "application/json"
            config["responseSchema"] = schema
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }
        token = await self._vertex_token()
        resp = await self._client.post(url, headers={"Authorization": f"Bearer {token}"}, json=body)
        resp.raise_for_status()
        data = resp.json()
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)

    async def _vertex_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        try:
            resp = await self._client.get(
                _METADATA_TOKEN_URL, headers={"Metadata-Flavor": "Google"}, timeout=2
            )
            resp.raise_for_status()
            data = resp.json()
            self._token, ttl = data["access_token"], int(data.get("expires_in", 300))
        except Exception:
            args = ["gcloud", "auth", "print-access-token"]
            if self.settings.gcloud_account:
                args.append(f"--account={self.settings.gcloud_account}")
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, err = await proc.communicate()
            if proc.returncode != 0:
                raise LLMUnavailable(f"gcloud token failed: {err.decode()[:200]}") from None
            self._token, ttl = out.decode().strip(), 3000
        self._token_expiry = time.time() + max(ttl - 120, 60)
        return self._token

    # ---- Anthropic ----------------------------------------------------------------------------

    async def _groq(self, system: str, prompt: str) -> str:
        key = self.settings.groq_api_key
        assert key is not None
        return await _groq_request(
            self._client,
            key.get_secret_value(),
            {
                "model": self.settings.llm_model,
                "temperature": 0,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
        )

    async def _anthropic(self, system: str, prompt: str) -> str:
        key = self.settings.anthropic_api_key
        assert key is not None
        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key.get_secret_value(),
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.settings.llm_model,
                "max_tokens": 8192,
                "temperature": 0,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        return "".join(b.get("text", "") for b in resp.json()["content"])


async def _groq_request(client: httpx.AsyncClient, key: str, body: dict[str, Any]) -> str:
    resp = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=body,
    )
    resp.raise_for_status()
    content: str = resp.json()["choices"][0]["message"]["content"] or ""
    return content


def _schema_hint(schema: dict[str, Any]) -> str:
    return "\n\nRespond with JSON only, matching this schema:\n" + json.dumps(schema)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()
