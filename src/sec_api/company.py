import asyncio

from pydantic import TypeAdapter
from typing_extensions import Literal

from .constants import DATA_SEC_URL
from .typings import DownloadResponse, Filing, Form, IDownloader, SubmissionsJSON
from .utils import (
    get_end_date,
    get_primary_document,
    get_start_date,
    transform_json_to_filings,
)

SubmissionsValidator = TypeAdapter(SubmissionsJSON)


class Company:
    _cik: str
    _downloader: IDownloader
    _filings: list[Filing] | None = None

    def __init__(self, cik: str | int, downloader: IDownloader):
        self._downloader = downloader
        self._cik = str(cik).rjust(10, "0")

    async def get_filing_details_async(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        form: Form | None = None,
        year: int | None = None,
        quarter: Literal[1, 2, 3, 4] | None = None,
        force: bool | None = None,
    ) -> list[Filing]:
        filings = await self._get_submissions_async(force)
        yyyy = None if year is None else str(year).rjust(4, "0")
        start_date = get_start_date(start_date, yyyy, quarter)
        end_date = get_end_date(end_date, yyyy, quarter)

        if start_date is None and end_date is None and form is None:
            return filings

        def filter_fn(f: Filing):
            report_date = f["reportDate"]
            return (
                (start_date is None or start_date <= report_date)
                and (end_date is None or end_date >= report_date)
                and (form is None or form == f["form"])
            )

        return list(filter(filter_fn, filings))

    async def get_primary_documents_async(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        form: Form | None = None,
        year: int | None = None,
        quarter: Literal[1, 2, 3, 4] | None = None,
        force: bool | None = None,
    ) -> list[DownloadResponse]:
        filings = await self.get_filing_details_async(
            start_date=start_date,
            end_date=end_date,
            form=form,
            year=year,
            quarter=quarter,
            force=force,
        )

        futures = map(self._get_primary_document_async, filings)
        return await asyncio.gather(*futures)

    async def _get_submissions_async(self, force: bool | None = False) -> list[Filing]:
        if force or self._filings is None:
            data = await self._downloader.get_url_async(
                url=f"{DATA_SEC_URL}/submissions/CIK{self._cik}.json"
            )
            self._filings = transform_json_to_filings(
                self._cik, SubmissionsValidator.validate_json(data["content"])
            )

        return self._filings

    async def _get_primary_document_async(self, filing: Filing) -> DownloadResponse:
        response = await self._downloader.get_url_async(get_primary_document(filing))
        return response
