from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .config import RunConfig
from .models import CTAIntent, PageAnalysis, PageSnapshot
from .utils import image_to_base64, image_to_data_uri


SYSTEM_PROMPT = """Analizujesz strony internetowe dla zespołów produktowych i delivery.

Otrzymasz:
1. Oczyszczony opis strony w formacie markdown
2. Zrzut ekranu tej samej strony

Zwróć wyłącznie JSON w takim kształcie:
{
  "dokumentacja_funkcjonalna": "krótki akapit",
  "historie_uzytkownika": [
    "Jako [Typ Użytkownika] chcę [Działanie], aby [Wartość]."
  ],
  "mapa_intencji": [
    {
      "cta": "etykieta przycisku lub głównego linku",
      "dlaczego": "motywacja użytkownika lub problem, który ta akcja rozwiązuje",
      "dowody": ["konkretny szczegół z markdown lub zrzutu ekranu"]
    }
  ]
}

Zasady:
- Nie wymyślaj funkcji, których nie widać w markdown ani na zrzucie ekranu.
- Jeśli dowody są słabe, zaznacz to wprost w treści odpowiedzi.
- Preferuj od 2 do 5 historii użytkownika.
- Skup mapę intencji na głównych CTA, a nie na drobnych linkach w stopce.
- Wykorzystuj podany kontekst biznesowy jako wskazówkę, ale nie pozwól, aby był ważniejszy niż faktyczne dowody ze strony.
- Wszystkie treści opisowe zwracaj po polsku.
"""


class Analyst:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.model = config.resolved_model()

    async def analyze(self, snapshot: PageSnapshot) -> PageAnalysis:
        if snapshot.screenshot_path is None:
            raise RuntimeError("Do analizy multimodalnej wymagany jest zrzut ekranu.")

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
        business_context = self.config.business_context or "Nie podano kontekstu biznesowego."
        return f"""Przeanalizuj tę stronę.

URL: {snapshot.url}
Tytuł: {snapshot.title}
Szablon: {snapshot.template_key}

Kontekst biznesowy:
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
            raise RuntimeError("Pakiet OpenAI SDK nie jest zainstalowany.") from exc

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
                raise RuntimeError("Do analizy przez Azure OpenAI wymagane są zmienne AZURE_API_KEY oraz AZURE_BASE_URL.")
            return api_key, base_url.rstrip("/")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Do analizy przez OpenAI wymagana jest zmienna OPENAI_API_KEY.")
        return api_key, None

    async def _request_anthropic(self, prompt: str, screenshot_path) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Do analizy przez Anthropic wymagana jest zmienna ANTHROPIC_API_KEY.")

        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:
            raise RuntimeError("Pakiet Anthropic SDK nie jest zainstalowany.") from exc

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
        raise ValueError(f"Odpowiedź modelu nie zawierała JSON-a: {payload[:200]}")
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
