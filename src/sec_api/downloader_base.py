import logging
from typing import override

import httpx
from httpx import AsyncHTTPTransport, Headers, Request, Response
from pyrate_limiter import Duration, Limiter, limiter_factory

from .constants import STATUS_CODE_NOT_MODIFIED
from .typings import DownloadResponse, IDownloader, ProxyType

logger = logging.getLogger(__name__)


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
    _proxy: ProxyType | None

    def __init__(
        self,
        *,
        user_agent: str,
        rate_per_second: int | None,
        proxy: ProxyType | None,
    ):
        # https://github.com/vutran1710/PyrateLimiter/blob/master/examples/httpx_ratelimiter.py
        self._limiter = limiter_factory.create_inmemory_limiter(
            rate_per_duration=rate_per_second or 5,
            duration=Duration.SECOND,
            max_delay=Duration.MINUTE,
            async_wrapper=True,
        )
        # https://www.sec.gov/about/webmaster-frequently-asked-questions#developers
        self._user_agent = user_agent
        self._proxy = proxy

    @override
    async def get_url_async(self, url: str) -> DownloadResponse:
        cached = await self.read_from_cache_async(url)

        response = await self._do_get_url_async(
            url=url,
            last_modified=None if cached is None else cached["last_modified"],
        )

        # There will be no content in response in case of STATUS_CODE_NOT_MODIFIED
        if cached is not None and response["status_code"] == STATUS_CODE_NOT_MODIFIED:
            return cached

        # Do not cache if server doesn't respond 'Last-Modified'
        # Otherwise everytime it will ignore cache, which will make cache irrelevant
        if response["last_modified"] == "":
            return response

        await self.write_to_cache_async(url, response)

        return response

    async def read_from_cache_async(self, url: str) -> DownloadResponse | None:
        return None

    async def write_to_cache_async(self, url: str, response: DownloadResponse):
        return None

    async def _do_get_url_async(
        self, *, url: str, last_modified: str | None
    ) -> DownloadResponse:
        transport = AsyncAsyncLimiterTransport(
            limiter=self._limiter, retries=3, proxy=self._proxy
        )
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
