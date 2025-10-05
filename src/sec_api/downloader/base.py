from abc import ABC, abstractmethod
from typing import TypedDict, override
from urllib.parse import urljoin

import httpx
from httpx import AsyncHTTPTransport, Headers, HTTPTransport, Request, Response
from pyrate_limiter import Duration, Limiter, Rate

STATUS_CODE_NOT_MODIFIED = 304


class DownloadResponse(TypedDict):
    url: str
    status_code: int
    content: str
    last_modified: str | None
    content_type: str | None


class IDownloader(ABC):
    @abstractmethod
    async def get_url_async(
        self, *, base_url: str, path: str, last_modified: str | None = None
    ) -> DownloadResponse:
        pass


class RateLimiterTransport(HTTPTransport):
    limiter: Limiter

    def __init__(self, limiter: Limiter, **kwargs):
        super().__init__(**kwargs)
        self.limiter = limiter

    @override
    def handle_request(self, request: Request, **kwargs) -> Response:
        # using a constant string for item name means that the same
        # rate is applied to all requests.
        acquired = self.limiter.try_acquire("httpx_ratelimiter")
        if not acquired:
            raise RuntimeError("Did not acquire lock")

        return super().handle_request(request, **kwargs)


class AsyncAsyncLimiterTransport(AsyncHTTPTransport):
    limiter: Limiter

    def __init__(self, limiter: Limiter, **kwargs):
        super().__init__(**kwargs)
        self.limiter = limiter

    @override
    async def handle_async_request(self, request: Request, **kwargs) -> Response:
        acquired = await self.limiter.try_acquire_async("httpx_ratelimiter")
        if not acquired:
            raise RuntimeError("Did not acquire lock")

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
        self._limiter = Limiter(
            Rate(rate_per_second, Duration.SECOND),
            max_delay=Duration.HOUR,
            raise_when_fail=True,
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
                    # "Host": "www.sec.gov",
                    "If-Modified-Since": last_modified or "",
                },
            )

        status_code = response.status_code
        _last_modified = response.headers.get("last-modified") or None
        content_type = response.headers.get("content-type") or None
        content = (
            response.text
            if status_code == STATUS_CODE_NOT_MODIFIED
            else response.raise_for_status().text
        )

        return {
            "status_code": status_code,
            "content": content,
            "last_modified": _last_modified,
            "url": url,
            "content_type": content_type,
        }
