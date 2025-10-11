import asyncio
import logging
import os

from dotenv import load_dotenv

from src.sec_api.cik import CentralIndexKey
from src.sec_api.company import Company
from src.sec_api.downloader_local import LocalCacheDownloader
from src.sec_api.typings import IDownloader

_ = load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class Edgar:
    _downloader: IDownloader
    _indexer: CentralIndexKey

    def __init__(self, *, downloader: IDownloader):
        self._downloader = downloader
        self._indexer = CentralIndexKey(downloader)

    async def get_company_async(
        self, *, cik: int | None = None, ticker: str | None = None
    ):
        if cik is None and ticker is not None:
            cik = await self._indexer.get_cik_by_ticker_async(ticker)

        if cik is None:
            return None

        return Company(cik=cik, downloader=self._downloader)


async def main_async():
    user_agent = os.environ.get("APP_USER_AGENT")

    if user_agent is None:
        return print("missing user agent")

    edgar = Edgar(downloader=LocalCacheDownloader(user_agent=user_agent))

    company = await edgar.get_company_async(ticker="ben")

    if company is None:
        return print("no company")

    documents = await company.get_primary_documents_async(
        form="10-Q", year=2024, quarter=1
    )

    print(documents[0]["content"])


if __name__ == "__main__":
    asyncio.run(main_async())
