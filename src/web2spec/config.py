from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .i18n import DEFAULT_LOCALE


@dataclass(slots=True)
class RunConfig:
    start_url: str
    output_dir: Path
    depth_limit: int = 2
    provider: str = "azure-openai"
    model: str | None = None
    skip_analysis: bool = False
    headless: bool = True
    capture_overlay: bool = True
    max_pages: int = 20
    request_timeout_ms: int = 20_000
    viewport_width: int = 1440
    viewport_height: int = 2200
    business_context: str | None = None
    browser_channel: str | None = None
    browser_executable_path: str | None = None
    show_progress: bool = True
    locale: str = DEFAULT_LOCALE

    def resolved_model(self) -> str:
        if self.model:
            return self.model
        if self.provider == "azure-openai":
            return "gpt-5.4"
        if self.provider == "anthropic":
            return "claude-3-5-sonnet-latest"
        return "gpt-4o"
