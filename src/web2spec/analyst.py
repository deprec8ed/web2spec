from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .config import RunConfig
from .models import CTAIntent, PageAnalysis, PageSnapshot
from .utils import image_to_base64, image_to_data_uri


SYSTEM_PROMPT = """You analyze website pages for product and delivery teams.

You will receive:
1. A cleaned markdown description of a page
2. A screenshot of the same page

Return JSON only with this shape:
{
  "functional_documentation": "short paragraph",
  "user_stories": [
    "As a [User Type], I want to [Action], so that [Value]."
  ],
  "intent_map": [
    {
      "cta": "label of button or primary link",
      "why": "the user motivation or problem this action solves",
      "evidence": ["specific supporting detail from markdown or screenshot"]
    }
  ]
}

Rules:
- Do not invent features that are not visible in the markdown or screenshot.
- If evidence is weak, say so explicitly in the wording.
- Prefer 2 to 5 user stories.
- Focus the intent map on primary CTAs, not every minor footer link.
- Use any provided business context as guidance, but never let it override the actual page evidence.
"""


class Analyst:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.model = config.resolved_model()

    async def analyze(self, snapshot: PageSnapshot) -> PageAnalysis:
        if snapshot.screenshot_path is None:
            raise RuntimeError("Screenshot is required for multimodal analysis.")

        prompt = self._build_prompt(snapshot)
        raw = await self._request(prompt, snapshot.screenshot_path)
        parsed = _extract_json(raw)

        return PageAnalysis(
            url=snapshot.url,
            functional_documentation=parsed.get("functional_documentation", "").strip(),
            user_stories=[story.strip() for story in parsed.get("user_stories", []) if story.strip()],
            intent_map=[
                CTAIntent(
                    cta=item.get("cta", "").strip(),
                    why=item.get("why", "").strip(),
                    evidence=[value.strip() for value in item.get("evidence", []) if value.strip()],
                )
                for item in parsed.get("intent_map", [])
                if item.get("cta") or item.get("why")
            ],
            raw_response=parsed,
        )

    def _build_prompt(self, snapshot: PageSnapshot) -> str:
        business_context = self.config.business_context or "No business context provided."
        return f"""Analyze this page.

URL: {snapshot.url}
Title: {snapshot.title}
Template: {snapshot.template_key}

Business Context:
{business_context}

Markdown:
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
                {"role": "system", "content": SYSTEM_PROMPT},
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
            system=SYSTEM_PROMPT,
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
