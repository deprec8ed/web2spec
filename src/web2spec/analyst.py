from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .config import RunConfig
from .i18n import get_text
from .models import CTAIntent, PageAnalysis, PageSnapshot
from .utils import image_to_base64, image_to_data_uri


class Analyst:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.model = config.resolved_model()
        self.text = get_text(config.locale)["analyst"]

    async def analyze(self, snapshot: PageSnapshot) -> PageAnalysis:
        if snapshot.screenshot_path is None:
            raise RuntimeError("Screenshot is required for multimodal analysis.")

        prompt = self._build_prompt(snapshot)
        raw = await self._request(prompt, snapshot.screenshot_path)
        parsed = _extract_json(raw)

        return PageAnalysis(
            url=snapshot.url,
            functional_documentation=_get_str(parsed, "dokumentacja_funkcjonalna", "functional_documentation"),
            user_stories=[
                story.strip()
                for story in _get_list(parsed, "historie_uzytkownika", "user_stories")
                if story.strip()
            ],
            intent_map=[
                CTAIntent(
                    cta=_get_str(item, "cta"),
                    why=_get_str(item, "dlaczego", "why"),
                    evidence=[value.strip() for value in _get_list(item, "dowody", "evidence") if value.strip()],
                )
                for item in _get_list(parsed, "mapa_intencji", "intent_map")
                if item.get("cta") or item.get("dlaczego") or item.get("why")
            ],
            raw_response=parsed,
        )

    def _build_prompt(self, snapshot: PageSnapshot) -> str:
        business_context = self.config.business_context or self.text["no_business_context"]
        return f"""{self.text['analyze_page']}

URL: {snapshot.url}
{self.text['title']}: {snapshot.title}
{self.text['template']}: {snapshot.template_key}

{self.text['business_context']}:
{business_context}

{self.text['markdown']}:
{snapshot.markdown}
"""

    async def _request(self, prompt: str, screenshot_path) -> str:
        if self.config.provider == "anthropic":
            return await self._request_anthropic(prompt, screenshot_path)
        return await self._request_openai(prompt, screenshot_path)

    async def _request_openai(self, prompt: str, screenshot_path: Path) -> str:
        api_key, base_url = self._resolve_openai_credentials()

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK is not installed.") from exc

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.text["system_prompt"]},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_to_data_uri(screenshot_path)}},
                    ],
                },
            ],
        )
        return response.choices[0].message.content or "{}"

    def _resolve_openai_credentials(self) -> tuple[str, str | None]:
        if self.config.provider == "azure-openai":
            api_key = os.environ.get("AZURE_API_KEY")
            base_url = os.environ.get("AZURE_BASE_URL")
            if not api_key or not base_url:
                raise RuntimeError("AZURE_API_KEY and AZURE_BASE_URL are required for Azure OpenAI analysis.")
            return api_key, base_url.rstrip("/")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI analysis.")
        return api_key, None

    async def _request_anthropic(self, prompt: str, screenshot_path) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic analysis.")

        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("Anthropic SDK is not installed.") from exc

        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=1400,
            system=self.text["system_prompt"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_to_base64(screenshot_path),
                            },
                        },
                    ],
                }
            ],
        )

        chunks = [block.text for block in response.content if getattr(block, "type", "") == "text"]
        return "\n".join(chunks)


def _extract_json(payload: str) -> dict[str, Any]:
    payload = payload.strip()
    if not payload:
        return {}

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", payload, re.DOTALL)
    if not match:
        raise ValueError(f"LLM response did not contain JSON: {payload[:200]}")
    return json.loads(match.group(0))


def _get_str(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _get_list(payload: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []
