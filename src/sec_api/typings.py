from abc import ABC, abstractmethod
from typing import Literal, TypedDict

from httpx import URL, Proxy

type Quarter = Literal[1, 2, 3, 4]

type Form = Literal[
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

type ProxyType = Proxy | URL | str


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


class SubmissionsJSON_Filings_File(TypedDict):
    name: str
    filingCount: int
    filingFrom: str
    filingTo: str


class SubmissionsJSON_Filings_Recent(TypedDict):
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


class SubmissionsJSON_Filings(TypedDict):
    recent: SubmissionsJSON_Filings_Recent
    files: list[SubmissionsJSON_Filings_File]


class SubmissionsJSON(TypedDict):
    filings: SubmissionsJSON_Filings


class DownloadResponse(TypedDict):
    url: str
    status_code: int
    content: str
    last_modified: str
    content_type: str | None


class IDownloader(ABC):
    @abstractmethod
    async def get_url_async(self, url: str) -> DownloadResponse:
        pass
