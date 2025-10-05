import logging
from abc import ABC, abstractmethod
from typing import TypedDict, override
from urllib.parse import urljoin

import httpx
from httpx import AsyncHTTPTransport, Headers, Request, Response
from pyrate_limiter import Duration, Limiter, limiter_factory

STATUS_CODE_NOT_MODIFIED = 304

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger.setLevel(logging.DEBUG)


class DownloadResponse(TypedDict):
    url: str
    status_code: int
    content: str
    last_modified: str
    content_type: str | None


class IDownloader(ABC):
    @abstractmethod
    async def get_url_async(
        self, *, base_url: str, path: str, last_modified: str | None = None
    ) -> DownloadResponse:
        pass


class AsyncAsyncLimiterTransport(AsyncHTTPTransport):
    limiter: Limiter

    def __init__(self, limiter: Limiter, **kwargs):
        super().__init__(**kwargs)
        self.limiter = limiter

    @override
    async def handle_async_request(self, request: Request, **kwargs) -> Response:
        while not await self.limiter.try_acquire_async("httpx_ratelimiter"):
            logger.debug("Lock acquisition timed out, retrying")

        logger.debug("Acquired lock")
        response = await super().handle_async_request(request, **kwargs)

        return response


def get_header(headers: Headers, key: str):
    try:
        return headers[key]
    except Exception:
        return ""


class BaseDownloader(IDownloader):
    _limiter: Limiter
    _user_agent: str

    def __init__(
        self, *, company_name: str, admin_email: str, rate_per_second: int = 5
    ):
        # https://github.com/vutran1710/PyrateLimiter/blob/master/examples/httpx_ratelimiter.py
        self._limiter = limiter_factory.create_inmemory_limiter(
            rate_per_duration=rate_per_second,
            duration=Duration.SECOND,
            max_delay=Duration.HOUR,
            async_wrapper=True,
        )
        # https://www.sec.gov/about/webmaster-frequently-asked-questions#developers
        self._user_agent = f"{company_name} {admin_email}"

    @override
    async def get_url_async(
        self, *, base_url: str, path: str, last_modified: str | None = None
    ) -> DownloadResponse:
        url = urljoin(base_url, path)
        transport = AsyncAsyncLimiterTransport(limiter=self._limiter, retries=3)
        async with httpx.AsyncClient(transport=transport) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept-Encoding": "gzip, deflate",
                    "If-Modified-Since": last_modified or "",
                },
            )

        status_code = response.status_code
        response_last_modified = response.headers.get("last-modified") or ""
        content_type = response.headers.get("content-type") or None
        content = (
            response.text
            if status_code == STATUS_CODE_NOT_MODIFIED
            else response.raise_for_status().text
        )

        return {
            "url": url,
            "status_code": status_code,
            "content": content,
            "content_type": content_type,
            "last_modified": response_last_modified,
        }
