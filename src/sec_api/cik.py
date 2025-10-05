from typing import Literal, TypedDict

from pydantic import TypeAdapter

from .downloader.base import IDownloader


class CompanyTickerExchange(TypedDict):
    cik: int
    name: str
    ticker: str
    exchange: str | None


class _CompanyTickersExchangeJson(TypedDict):
    fields: tuple[
        Literal["cik"], Literal["name"], Literal["ticker"], Literal["exchange"]
    ]
    data: list[tuple[int, str, str, str | None]]


class _StructuredData(TypedDict):
    list: list[CompanyTickerExchange]
    by_cik: dict[int, CompanyTickerExchange]
    by_ticker: dict[str, CompanyTickerExchange]


def _structure_data(raw_data: _CompanyTickersExchangeJson):
    structured_data: _StructuredData = {"list": [], "by_cik": {}, "by_ticker": {}}

    for row in raw_data["data"]:
        item: CompanyTickerExchange = {
            "cik": row[0],
            "name": row[1],
            "ticker": row[2],
            "exchange": row[3],
        }

        structured_data["list"].append(item)
        structured_data["by_cik"][row[0]] = item
        structured_data["by_ticker"][row[2]] = item

    return structured_data


class CentralIndexKey:
    _downloader: IDownloader
    _last_modified: str | None = None
    _structured_data: _StructuredData | None = None

    def __init__(self, downloader: IDownloader):
        self._downloader = downloader

    async def get_by_ticker_async(self, ticker: str) -> CompanyTickerExchange | None:
        structured_data = await self._get_structured_data()
        if structured_data is None:
            return None
        return structured_data["by_ticker"].get(ticker.upper())

    async def get_cik_by_ticker_async(self, ticker: str) -> int | None:
        co = await self.get_by_ticker_async(ticker)
        return None if co is None else co["cik"]

    async def get_by_cik_async(self, cik: int) -> CompanyTickerExchange | None:
        structured_data = await self._get_structured_data()
        if structured_data is None:
            return None
        return structured_data["by_cik"].get(cik)

    async def get_all_async(self) -> list[CompanyTickerExchange] | None:
        structured_data = await self._get_structured_data()
        if structured_data is None:
            return None
        return structured_data["list"]

    async def _get_structured_data(self) -> _StructuredData | None:
        response = await self._downloader.get_url_async(
            base_url="https://www.sec.gov", path="files/company_tickers_exchange.json"
        )

        last_modified = response["last_modified"]

        if last_modified == "" or last_modified != self._last_modified:
            adapter = TypeAdapter(_CompanyTickersExchangeJson)
            company_tickers_exchange_json = adapter.validate_json(response["content"])
            self._structured_data = _structure_data(company_tickers_exchange_json)
            self._last_modified = last_modified

        return self._structured_data
