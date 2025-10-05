import json
from pathlib import Path
from typing import override

from pydantic import TypeAdapter

from .base import STATUS_CODE_NOT_MODIFIED, BaseDownloader, DownloadResponse

DownloadResponseValidator = TypeAdapter(DownloadResponse)


class LocalCacheDownloader(BaseDownloader):
    _cache_directory: str

    def __init__(self, *, cache_directory: str, company_name: str, admin_email: str):
        super().__init__(company_name=company_name, admin_email=admin_email)
        self._cache_directory = cache_directory

    @override
    async def get_url_async(
        self, *, base_url: str, path: str, last_modified: str | None = None
    ) -> DownloadResponse:
        cached = self._read_from_cache(path)

        response = await super().get_url_async(
            base_url=base_url,
            path=path,
            last_modified=None if cached is None else cached["last_modified"],
        )

        # There will be no content in response in case of STATUS_CODE_NOT_MODIFIED
        if cached is not None and response["status_code"] is STATUS_CODE_NOT_MODIFIED:
            return cached

        # Do not cache is server doesn't respond 'Last-Modified'
        # Otherwise everytime it will ignore cache,which will make cache irrelevant
        if response["last_modified"] is None:
            return response

        return self._write_to_cache(path, response)

    def _read_from_cache(self, path: str) -> DownloadResponse | None:
        fname = Path(self._cache_directory, path)
        if fname.exists():
            with open(fname) as file:
                content = file.read()
        else:
            return None

        try:
            return DownloadResponseValidator.validate_json(content)
        except Exception:
            return None

    def _write_to_cache(
        self, path: str, response: DownloadResponse
    ) -> DownloadResponse:
        fname = Path(self._cache_directory, path)
        fname.parent.mkdir(exist_ok=True, parents=True)
        with open(fname, "w") as file:
            _ = file.write(json.dumps(response, indent=2))
        return response
