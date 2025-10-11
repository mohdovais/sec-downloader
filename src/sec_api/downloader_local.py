import json
from pathlib import Path
from typing import override
from urllib.parse import urlsplit

from pydantic import TypeAdapter

from .downloader_base import BaseDownloader
from .typings import DownloadResponse, ProxyType

DownloadResponseValidator = TypeAdapter(DownloadResponse)


class LocalCacheDownloader(BaseDownloader):
    _cache_directory: str

    def __init__(
        self,
        *,
        user_agent: str,
        cache_directory: str = ".data",
        rate_per_second: int | None = None,
        proxy: ProxyType | None = None,
    ):
        super().__init__(
            user_agent=user_agent, rate_per_second=rate_per_second, proxy=proxy
        )
        self._cache_directory = cache_directory

    @override
    def read_from_cache(self, url: str) -> DownloadResponse | None:
        fname = Path(self._cache_directory, urlsplit(url).path.lstrip("/"))
        if fname.exists():
            with open(fname) as file:
                content = file.read()
        else:
            return None

        try:
            return DownloadResponseValidator.validate_json(content)
        except Exception:
            return None

    @override
    def write_to_cache(self, url: str, response: DownloadResponse) -> DownloadResponse:
        fname = Path(self._cache_directory, urlsplit(url).path.lstrip("/"))
        fname.parent.mkdir(exist_ok=True, parents=True)
        with open(fname, "w") as file:
            _ = file.write(json.dumps(response, indent=2))
        return response
