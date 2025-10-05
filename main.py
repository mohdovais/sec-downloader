import asyncio
import json


from src.sec_api.company import Company
from src.sec_api.downloader.local_cache import LocalCacheDownloader


async def main_async():
    sec_downloader = LocalCacheDownloader(
        cache_directory="data",
        company_name="personal project",
        admin_email="john.doe@gmail.com",
    )
    co = Company(38777, downloader=sec_downloader)

    documents = await co.get_filing_documents_async(form="10-Q", year=2024, quarter=1)
    print(json.dumps(documents, indent=2))


if __name__ == "__main__":
    asyncio.run(main_async())
