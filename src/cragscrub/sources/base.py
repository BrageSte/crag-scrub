from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Iterable, Optional

import requests
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from cragscrub.models import Crag, Region

USER_AGENT = "crag-scrub/0.1 (+https://github.com/BrageSte/crag-scrub)"


def _default_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


class BaseScraper(ABC):
    def __init__(
        self,
        base_url: str,
        session: Optional[requests.Session] = None,
        min_delay: float = 1.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or _default_session()
        self.min_delay = min_delay
        self._last_request_ts: Optional[float] = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _get(self, path: str, **kwargs) -> requests.Response:
        self._throttle()
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        response = self.session.get(url, timeout=20, **kwargs)
        response.raise_for_status()
        return response

    def _throttle(self) -> None:
        if self._last_request_ts is None:
            self._last_request_ts = time.time()
            return
        elapsed = time.time() - self._last_request_ts
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_request_ts = time.time()

    @abstractmethod
    def iter_regions(self, scope: dict | None = None) -> Iterable[Region]:
        """Yield `Region` objects honoring the provided scope (e.g., country codes)."""

    @abstractmethod
    def iter_crags(self, scope: dict | None = None) -> Iterable[Crag]:
        """Yield `Crag` objects honoring the provided scope (e.g., country codes)."""

    def safe_iter(self, iterator: Iterable[Crag | Region]) -> Iterable[Crag | Region]:
        """Wrap an iterator so RetryError raises are surfaced with context."""

        try:
            yield from iterator
        except RetryError as exc:  # pragma: no cover - passthrough helper
            raise RuntimeError(f"Retries exhausted for {self.__class__.__name__}") from exc
