import asyncio

from src.sec_api.company import Company
from src.sec_api.downloader.local_cache import LocalCacheDownloader
from src.sec_api.cik import CentralIndexKey


async def main_async():
    sec_downloader = LocalCacheDownloader(
        cache_directory="data",
        company_name="personal project",
        admin_email="john.doe@gmail.com",
    )
    indices = CentralIndexKey(sec_downloader)

    cik = await indices.get_cik_by_ticker_async("ben")

    if cik is None:
        print("Unable to find CIK")
        return

    co = Company(cik=cik, downloader=sec_downloader)
    documents = await co.get_filing_documents_async(form="10-Q", year=2024, quarter=1)

    print(documents[0]["content"])


if __name__ == "__main__":
    asyncio.run(main_async())
