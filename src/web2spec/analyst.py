from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .config import RunConfig
from .i18n import get_text
from .models import CTAIntent, GuideSection, GuideStep, PageAnalysis, PageSnapshot
from .utils import image_to_base64, image_to_data_uri


class Analyst:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.model = config.resolved_model()
        self.text = get_text(config.locale)["analyst"]
        self.guide_text = get_text(config.locale)["guide"]

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

    async def analyze_for_guide(self, snapshot: PageSnapshot) -> GuideSection:
        if snapshot.screenshot_path is None:
            raise RuntimeError("Screenshot is required for guide generation.")

        prompt = self._build_guide_prompt(snapshot)
        raw = await self._request_guide(prompt, snapshot.screenshot_path)
        parsed = _extract_json(raw)

        steps = []
        for idx, step_data in enumerate(_get_list(parsed, "steps"), 1):
            step = GuideStep(
                step_number=idx,
                heading=_get_str(step_data, "heading"),
                action_bullets=[
                    bullet.strip()
                    for bullet in _get_list(step_data, "action_bullets")
                    if isinstance(bullet, str) and bullet.strip()
                ],
                what_you_see=_get_str(step_data, "what_you_see"),
                screenshot_path=snapshot.screenshot_path,
            )
            steps.append(step)

        return GuideSection(
            url=snapshot.url,
            depth=snapshot.depth,
            title=_get_str(parsed, "section_title"),
            intro=_get_str(parsed, "intro"),
            steps=steps if steps else self._fallback_steps(snapshot),
            parent_url=snapshot.parent_url,
        )

    def _fallback_steps(self, snapshot: PageSnapshot) -> list[GuideStep]:
        """Fallback when LLM doesn't return steps: create a minimal step from the markdown."""
        return [
            GuideStep(
                step_number=1,
                heading=snapshot.title,
                action_bullets=["Review the visible goal-related controls on this page."],
                what_you_see=snapshot.markdown[:200] + "..." if snapshot.markdown else snapshot.title,
                screenshot_path=snapshot.screenshot_path,
            )
        ]

    async def decide_next_links(self, snapshot: PageSnapshot) -> list[str]:
        """Ask the LLM which internal links on this page should be followed to achieve the goal."""
        goal = self.config.goal_context or ""
        if not goal:
            return snapshot.internal_links

        nav_text = get_text(self.config.locale)["navigator"]
        valid_internal: set[str] = set(snapshot.internal_links)

        # Build a compact label→url map from anchor elements
        link_map: dict[str, str] = {}
        for el in snapshot.elements:
            if el.tag == "a" and el.href and el.href in valid_internal:
                label = (el.text or el.aria_label or "").strip()[:80]
                if label and label not in link_map:
                    link_map[label] = el.href

        if not link_map:
            return []

        link_lines = "\n".join(f"  [{label}] -> {url}" for label, url in link_map.items())
        prompt = (
            f"Goal: {goal}\n\n"
            f"Page: {snapshot.url}\n"
            f"Title: {snapshot.title}\n\n"
            f"Available links:\n{link_lines}\n\n"
            "Which links should be followed to achieve this goal?"
        )

        raw = await self._request_text_only(prompt, system_prompt=nav_text["system_prompt"])
        parsed = _extract_json(raw)

        follow_items = _get_list(parsed, "follow")
        result: list[str] = []
        for item in follow_items:
            url = item.get("url", "") if isinstance(item, dict) else str(item)
            if not url:
                continue
            # Exact match first
            if url in valid_internal:
                if url not in result:
                    result.append(url)
                continue
            # Substring / suffix match (LLM may return path only)
            matched = next(
                (u for u in valid_internal if url and (u.endswith(url) or url in u)),
                None,
            )
            if matched and matched not in result:
                result.append(matched)
                continue
            # Reverse lookup: LLM returned a visible label instead of URL
            if url in link_map and link_map[url] not in result:
                result.append(link_map[url])

        return result

    async def _request_text_only(self, prompt: str, system_prompt: str) -> str:
        if self.config.provider == "anthropic":
            return await self._request_anthropic_text(prompt, system_prompt)
        return await self._request_openai_text(prompt, system_prompt)

    async def _request_openai_text(self, prompt: str, system_prompt: str) -> str:
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or "{}"

    async def _request_anthropic_text(self, prompt: str, system_prompt: str) -> str:
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
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else "{}"

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

    def _build_guide_prompt(self, snapshot: PageSnapshot) -> str:
        business_context = self.config.business_context or self.guide_text["no_business_context"]
        goal_context = self.config.goal_context or self.guide_text["no_goal_context"]
        return f"""{self.guide_text['analyze_page']}

URL: {snapshot.url}
{self.guide_text['title']}: {snapshot.title}
{self.guide_text['template']}: {snapshot.template_key}

{self.guide_text['business_context']}:
{business_context}

{self.guide_text['goal_context']}:
{goal_context}

{self.guide_text['intent_scope_rules']}

{self.guide_text['markdown']}:
{snapshot.markdown}
"""

    async def _request(self, prompt: str, screenshot_path) -> str:
        if self.config.provider == "anthropic":
            return await self._request_anthropic(prompt, screenshot_path)
        return await self._request_openai(prompt, screenshot_path)

    async def _request_guide(self, prompt: str, screenshot_path) -> str:
        if self.config.provider == "anthropic":
            return await self._request_anthropic(prompt, screenshot_path, system_prompt=self.guide_text["system_prompt"])
        return await self._request_openai(prompt, screenshot_path, system_prompt=self.guide_text["system_prompt"])

    async def _request_openai(self, prompt: str, screenshot_path: Path, system_prompt: str | None = None) -> str:
        api_key, base_url = self._resolve_openai_credentials()
        system = system_prompt or self.text["system_prompt"]

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI SDK is not installed.") from exc

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
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

    async def _request_anthropic(self, prompt: str, screenshot_path, system_prompt: str | None = None) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for Anthropic analysis.")
        system = system_prompt or self.text["system_prompt"]

        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("Anthropic SDK is not installed.") from exc

        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=self.model,
            max_tokens=1400,
            system=system,
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
