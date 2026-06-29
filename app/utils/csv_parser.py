import csv
import io
from datetime import datetime
from typing import Any, Dict, List
from app.core.exceptions import InvalidCSVException

REQUIRED_COLUMNS = {"txn_id", "date", "merchant", "amount"}


def parse_and_validate_csv(content: bytes) -> List[Dict[str, Any]]:
    """
    Parses CSV content from bytes, validates headers, and checks field types.
    Supports flexible mapping of common synonyms for headers.
    Returns a list of dicts. Raises InvalidCSVException if the file is invalid.
    """
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise InvalidCSVException("CSV file must be UTF-8 encoded text") from e

    csv_file = io.StringIO(decoded)
    reader = csv.DictReader(csv_file)

    if not reader.fieldnames:
        raise InvalidCSVException("CSV file is empty or missing headers")

    header_mapping = {}
    for actual_header in reader.fieldnames:
        if not actual_header:
            continue
        cleaned = actual_header.strip().lower()

        # Map synonyms
        if cleaned in {"txn_id", "transaction_id", "id"}:
            header_mapping["txn_id"] = actual_header
        elif cleaned == "date":
            header_mapping["date"] = actual_header
        elif cleaned in {"merchant", "description"}:
            header_mapping["merchant"] = actual_header
        elif cleaned == "amount":
            header_mapping["amount"] = actual_header
        elif cleaned == "currency":
            header_mapping["currency"] = actual_header
        elif cleaned == "category":
            header_mapping["category"] = actual_header
        elif cleaned in {"account_id", "account"}:
            header_mapping["account_id"] = actual_header

    # Verify all required columns are present in mapping
    missing = REQUIRED_COLUMNS - set(header_mapping.keys())
    if missing:
        raise InvalidCSVException(f"Missing required CSV columns: {', '.join(missing)}")

    parsed_rows = []
    for line_num, row in enumerate(reader, start=2):
        txn_id = row.get(header_mapping["txn_id"])
        date_str = row.get(header_mapping["date"])
        amount_str = row.get(header_mapping["amount"])
        merchant = row.get(header_mapping["merchant"])

        # Optional columns
        currency = (
            row.get(header_mapping.get("currency", ""))
            if "currency" in header_mapping
            else "INR"
        )
        category = (
            row.get(header_mapping.get("category", ""))
            if "category" in header_mapping
            else None
        )
        account_id = (
            row.get(header_mapping.get("account_id", ""))
            if "account_id" in header_mapping
            else None
        )

        if not all([txn_id, date_str, amount_str, merchant]):
            raise InvalidCSVException(
                f"Row {line_num}: Empty values are not allowed in required fields"
            )

        # Validate amount
        try:
            amount = float(amount_str.strip())
        except ValueError as e:
            raise InvalidCSVException(
                f"Row {line_num}: Invalid amount '{amount_str}'. Must be a number."
            ) from e

        # Validate date (supporting multiple formats)
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                break
            except ValueError:
                continue

        if not parsed_date:
            raise InvalidCSVException(
                f"Row {line_num}: Invalid date format '{date_str}'. Expected YYYY-MM-DD or MM/DD/YYYY"
            )

        parsed_rows.append(
            {
                "txn_id": txn_id.strip(),
                "date": parsed_date.isoformat(),
                "amount": amount,
                "merchant": merchant.strip(),
                "currency": currency.strip() if currency else "INR",
                "category": category.strip() if category else None,
                "account_id": account_id.strip() if account_id else None,
            }
        )

    if not parsed_rows:
        raise InvalidCSVException("CSV file contains no data rows")

    return parsed_rows
