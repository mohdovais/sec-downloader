from datetime import datetime

from .constants import SEC_URL
from .typings import Filing, Quarter, SubmissionsJSON


def valid_date_string(date_string: str) -> bool:
    try:
        # The `strptime` method will raise a ValueError if the format does not match
        _ = datetime.strptime(date_string, "%Y-%m-%d").date()
        return True
    except ValueError:
        return False


def get_start_date(
    start_date: str | None = None,
    year: str | None = None,
    quarter: Quarter | None = None,
) -> str | None:
    if start_date is not None and valid_date_string(start_date):
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


def get_end_date(
    end_date: str | None = None,
    year: str | None = None,
    quarter: Quarter | None = None,
) -> str | None:
    if end_date is not None and valid_date_string(end_date):
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


def transform_json_to_filings(cik: str, data: SubmissionsJSON) -> list[Filing]:
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


def get_primary_document(filing: Filing) -> str:
    cik = filing["cik"].lstrip("0")
    accn = filing["accessionNumber"].replace("-", "")
    doc = filing["primaryDocument"]

    return f"{SEC_URL}/Archives/edgar/data/{cik}/{accn}/{doc}"
