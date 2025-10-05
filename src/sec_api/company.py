import asyncio
from typing import TypedDict

from pydantic import TypeAdapter
from typing_extensions import Literal

from .downloader.base import IDownloader

SEC_URL = "https://www.sec.gov"
DATA_SEC_URL = "https://data.sec.gov"


class FilingFile(TypedDict):
    name: str
    filingCount: int
    filingFrom: str
    filingTo: str


class RecentFilings(TypedDict):
    accessionNumber: list[str]
    filingDate: list[str]
    reportDate: list[str]
    acceptanceDateTime: list[str]
    act: list[str]
    form: list[str]
    fileNumber: list[str]
    filmNumber: list[str]
    items: list[str]
    core_type: list[str]
    size: list[int]
    isXBRL: list[int]
    isInlineXBRL: list[int]
    primaryDocument: list[str]
    primaryDocDescription: list[str]


class Filings(TypedDict):
    recent: RecentFilings
    files: list[FilingFile]


class Submissions(TypedDict):
    filings: Filings


SubmissionsValidator = TypeAdapter(Submissions)

Form = Literal[
    "10-K",
    "10-Q",
    "11-K",
    "13F-HR",
    "13F-HR/A",
    "144",
    "3",
    "4",
    "4/A",
    "40-6B",
    "424B2",
    "424B5",
    "5",
    "5/A",
    "8-K",
    "8-K/A",
    "ARS",
    "DEF 14A",
    "DEFA14A",
    "DEFR14A",
    "DFAN14A",
    "FWP",
    "N-PX",
    "S-3",
    "S-3ASR",
    "S-8",
    "SC 13D",
    "SC 13D/A",
    "SC 13G",
    "SC 13G/A",
    "SCHEDULE 13D/A",
    "SCHEDULE 13G",
    "SCHEDULE 13G/A",
]


class Filing(TypedDict):
    cik: str
    accessionNumber: str
    filingDate: str
    reportDate: str
    acceptanceDateTime: str
    act: str
    form: str
    fileNumber: str
    filmNumber: str
    items: str
    core_type: str
    size: int
    isXBRL: int
    isInlineXBRL: int
    primaryDocument: str
    primaryDocDescription: str


def _transform(cik: str, data: Submissions):
    recent = data["filings"]["recent"]
    transformed: list[Filing] = []

    for i in range(0, len(recent["accessionNumber"]) - 1):
        transformed.append(
            {
                "cik": cik,
                "acceptanceDateTime": recent["acceptanceDateTime"][i],
                "accessionNumber": recent["accessionNumber"][i],
                "act": recent["act"][i],
                "core_type": recent["core_type"][i],
                "fileNumber": recent["fileNumber"][i],
                "filingDate": recent["filingDate"][i],
                "filmNumber": recent["filmNumber"][i],
                "form": recent["form"][i],
                "isInlineXBRL": recent["isInlineXBRL"][i],
                "isXBRL": recent["isXBRL"][i],
                "items": recent["items"][i],
                "primaryDocDescription": recent["primaryDocDescription"][i],
                "primaryDocument": recent["primaryDocument"][i],
                "reportDate": recent["reportDate"][i],
                "size": recent["size"][i],
            }
        )

    return transformed


def _get_start_date(
    start_date: str | None = None,
    year: str | None = None,
    quarter: Literal[1, 2, 3, 4] | None = None,
):
    if start_date is not None:
        return start_date

    if year is None:
        return None

    if quarter is None or quarter == 1:
        return f"{year}-01-01"

    if quarter == 2:
        return f"{year}-04-01"

    if quarter == 3:
        return f"{year}-07-01"

    if quarter == 4:
        return f"{year}-10-01"


def _get_end_date(
    end_date: str | None = None,
    year: str | None = None,
    quarter: Literal[1, 2, 3, 4] | None = None,
):
    if end_date is not None:
        return end_date

    if year is None:
        return None

    if quarter is None or quarter == 4:
        return f"{year}-12-31"

    if quarter == 1:
        return f"{year}-03-31"

    if quarter == 2:
        return f"{year}-06-30"

    if quarter == 3:
        return f"{year}-09-30"


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
    ):
        filings = await self._get_submissions_async(force)
        yyyy = None if year is None else str(year).rjust(4, "0")
        start_date = _get_start_date(start_date, yyyy, quarter)
        end_date = _get_end_date(end_date, yyyy, quarter)

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

    async def get_filing_documents_async(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        form: Form | None = None,
        year: int | None = None,
        quarter: Literal[1, 2, 3, 4] | None = None,
        force: bool | None = None,
    ):
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

    async def _get_submissions_async(self, force: bool | None = False):
        if force or self._filings is None:
            data = await self._downloader.get_url_async(
                base_url=DATA_SEC_URL, path=f"submissions/CIK{self._cik}.json"
            )
            self._filings = _transform(
                self._cik, SubmissionsValidator.validate_json(data["content"])
            )

        return self._filings

    async def _get_primary_document_async(self, filing: Filing):
        cik = filing["cik"].lstrip("0")
        accn = filing["accessionNumber"].replace("-", "")
        doc = filing["primaryDocument"]

        return await self._downloader.get_url_async(
            base_url=SEC_URL, path=f"Archives/edgar/data/{cik}/{accn}/{doc}"
        )
