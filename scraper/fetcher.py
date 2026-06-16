import asyncio
import logging
import time

import httpx
from app.config import get_settings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class RateLimitedFetcher:
    def __init__(self, rate_limit_seconds: float | None = None, user_agent: str | None = None) -> None:
        settings = get_settings()
        self.rate_limit_seconds = rate_limit_seconds or settings.scraper_rate_limit_seconds
        self.user_agent = user_agent or settings.scraper_user_agent
        self._last_request_at = 0.0

    async def _wait_for_slot(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.rate_limit_seconds - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def fetch(self, url: str) -> str:
        await self._wait_for_slot()
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
            logger.info("Fetching schedule source: %s", url)
            response = await client.get(url)
            self._last_request_at = time.monotonic()
            response.raise_for_status()
            return response.text

