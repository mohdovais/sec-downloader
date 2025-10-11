import json
from typing import override
from unittest.mock import AsyncMock

import pytest

from src.sec_api.constants import COMPANY_TICKERS_EXCHANGE_URL

from .cik import (
    CentralIndexKey,
    StructuredCompanyTickerExchange,
    structure_company_exchange_json,
)
from .typings import DownloadResponse, IDownloader


@pytest.fixture
def mock_raw_data_success() -> DownloadResponse:
    """Mock a successful downloader response with sample ticker data."""

    content = json.dumps(
        {
            "fields": ("cik", "name", "ticker", "exchange"),
            "data": [
                (123, "Apple Inc.", "AAPL", "NASDAQ"),
                (456, "Microsoft Corp.", "MSFT", "NASDAQ"),
                (789, "Alphabet Inc.", "GOOG", None),
            ],
        }
    )

    return {
        "url": COMPANY_TICKERS_EXCHANGE_URL,
        "status_code": 200,
        "content": content,
        "last_modified": "",
        "content_type": None,
    }


@pytest.fixture
def mock_raw_data_empty() -> DownloadResponse:
    """Mock a downloader response with no ticker data."""

    content = json.dumps(
        {
            "fields": ("cik", "name", "ticker", "exchange"),
            "data": [],
        }
    )

    return {
        "url": COMPANY_TICKERS_EXCHANGE_URL,
        "status_code": 200,
        "content": content,
        "last_modified": "",
        "content_type": None,
    }


@pytest.fixture
def mock_downloader(mock_raw_data_success: dict[str, str]) -> IDownloader:
    """Fixture to provide a mocked IDownloader instance."""

    class MockDownloader(IDownloader):
        @override
        async def get_url_async(self, url: str) -> DownloadResponse:
            return await super().get_url_async(url)

    object = MockDownloader()
    object.get_url_async = AsyncMock(return_value=mock_raw_data_success)
    return object


@pytest.fixture
def mock_errornemous_downloader() -> IDownloader:
    """Fixture to provide a mocked IDownloader instance."""

    class MockDownloader(IDownloader):
        @override
        async def get_url_async(self, url: str) -> DownloadResponse:
            raise ConnectionError("404")

    return MockDownloader()


# --- Tests for structure_company_exchange_json ---


def test_structure_company_exchange_json_success(
    mock_raw_data_success: dict[str, str],
) -> None:
    """Test that structure_company_exchange_json correctly processes raw data."""
    raw_content = json.loads(mock_raw_data_success["content"])
    structured: StructuredCompanyTickerExchange = structure_company_exchange_json(
        raw_content  # type: ignore
    )

    assert len(structured["list"]) == 3
    assert len(structured["by_cik"]) == 3
    assert len(structured["by_ticker"]) == 3

    # Check 'list' structure
    aapl_data = next(item for item in structured["list"] if item["ticker"] == "AAPL")
    assert aapl_data["cik"] == 123
    assert aapl_data["ticker"] == "AAPL"

    # Check 'by_cik' mapping
    msft_data = structured["by_cik"][456]
    assert msft_data["name"] == "Microsoft Corp."

    # Check 'by_ticker' mapping
    assert structured["by_ticker"]["AAPL"]["cik"] == 123
    assert structured["by_ticker"]["GOOG"]["exchange"] is None


def test_structure_company_exchange_json_empty(
    mock_raw_data_empty: dict[str, str],
) -> None:
    """Test that function handles empty data gracefully."""
    raw_content = json.loads(mock_raw_data_empty["content"])
    structured: StructuredCompanyTickerExchange = structure_company_exchange_json(
        raw_content  # type: ignore
    )
    assert structured["list"] == []
    assert structured["by_cik"] == {}
    assert structured["by_ticker"] == {}


# --- Tests for CentralIndexKey class ---


@pytest.mark.asyncio
async def test_get_by_ticker_async_success(
    mock_downloader: IDownloader,
):
    """Test get_by_ticker_async returns the correct company for a given ticker."""
    cik_instance = CentralIndexKey(mock_downloader)
    company = await cik_instance.get_by_ticker_async("AAPL")
    assert company is not None
    assert company["cik"] == 123
    assert company["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_get_by_ticker_async_not_found(
    mock_downloader: IDownloader,
):
    """Test get_by_ticker_async returns None for a non-existent ticker."""
    cik_instance = CentralIndexKey(mock_downloader)
    company = await cik_instance.get_by_ticker_async("NONEXISTENT")
    assert company is None


@pytest.mark.asyncio
async def test_get_by_ticker_async_case_insensitivity(
    mock_downloader: IDownloader,
):
    """Test get_by_ticker_async handles case-insensitive tickers."""
    cik_instance = CentralIndexKey(mock_downloader)
    company = await cik_instance.get_by_ticker_async("aapl")
    assert company is not None
    assert company["ticker"] == "AAPL"


@pytest.mark.asyncio
async def test_get_cik_by_ticker_async_success(
    mock_downloader: IDownloader,
):
    """Test get_cik_by_ticker_async returns the correct CIK."""
    cik_instance = CentralIndexKey(mock_downloader)
    cik = await cik_instance.get_cik_by_ticker_async("AAPL")
    assert cik == 123


@pytest.mark.asyncio
async def test_get_cik_by_ticker_async_not_found(
    mock_downloader: IDownloader,
):
    """Test get_cik_by_ticker_async returns None for non-existent ticker."""
    cik_instance = CentralIndexKey(mock_downloader)
    cik = await cik_instance.get_cik_by_ticker_async("NONEXISTENT")
    assert cik is None


@pytest.mark.asyncio
async def test_get_by_cik_async_success(
    mock_downloader: IDownloader,
):
    """Test get_by_cik_async returns the correct company for a given CIK."""
    cik_instance = CentralIndexKey(mock_downloader)
    company = await cik_instance.get_by_cik_async(456)
    assert company is not None
    assert company["ticker"] == "MSFT"


@pytest.mark.asyncio
async def test_get_by_cik_async_not_found(
    mock_downloader: IDownloader,
):
    """Test get_by_cik_async returns None for a non-existent CIK."""
    cik_instance = CentralIndexKey(mock_downloader)
    company = await cik_instance.get_by_cik_async(999)
    assert company is None


@pytest.mark.asyncio
async def test_get_all_async_success(
    mock_downloader: IDownloader,
):
    """Test get_all_async returns the full list of companies."""
    cik_instance = CentralIndexKey(mock_downloader)
    all_companies = await cik_instance.get_all_async()
    assert all_companies is not None
    assert len(all_companies) == 3
    assert any(co["ticker"] == "GOOG" for co in all_companies)


@pytest.mark.asyncio
async def test_get_all_async_empty_data(
    mock_downloader: IDownloader,
    mock_raw_data_empty: dict[str, str],
):
    """Test get_all_async handles an empty data set from the downloader."""
    mock_downloader.get_url_async.return_value = mock_raw_data_empty
    cik_instance = CentralIndexKey(mock_downloader)
    all_companies = await cik_instance.get_all_async()
    assert all_companies is not None
    assert len(all_companies) == 0


@pytest.mark.asyncio
async def test_caching_mechanism(mock_downloader: IDownloader):
    """Test that the downloader is only called once if data is fresh."""
    cik_instance = CentralIndexKey(mock_downloader)

    # First call, should trigger a downloader call
    _ = await cik_instance.get_by_ticker_async("AAPL")
    mock_downloader.get_url_async.assert_called_once()

    # @TODO


@pytest.mark.asyncio
async def test_downloader_failure_returns_none(
    mock_errornemous_downloader: IDownloader,
):
    """Test that a downloader failure results in None being returned."""
    cik_instance = CentralIndexKey(mock_errornemous_downloader)

    with pytest.raises(ConnectionError):
        _ = await cik_instance.get_by_ticker_async("AAPL")
