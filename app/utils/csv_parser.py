import csv
import io
from datetime import datetime
from typing import Any, Dict, List
from app.core.exceptions import InvalidCSVException

REQUIRED_COLUMNS = {"transaction_id", "date", "amount", "category", "description"}


def parse_and_validate_csv(content: bytes) -> List[Dict[str, Any]]:
    csv_file = io.StringIO(decoded)
    reader = csv.DictReader(csv_file)

    # Map headers to predefined required cols
    headers = {h.strip().lower() for h in reader.fieldnames if h}
    header_mapping = {}
    for actual_header in reader.fieldnames:
        cleaned = actual_header.strip().lower()
        if cleaned in REQUIRED_COLUMNS:
            header_mapping[cleaned] = actual_header
        elif cleaned == "id" and "transaction_id" not in header_mapping:
            header_mapping["transaction_id"] = actual_header

    missing = REQUIRED_COLUMNS - set(header_mapping.keys())
    if missing:
        raise InvalidCSVException(f"Missing required CSV columns: {', '.join(missing)}")

    parsed_rows = []
    for line_num, row in enumerate(reader, start=2):
        t_id = row.get(header_mapping["transaction_id"])
        date_str = row.get(header_mapping["date"])
        amount_str = row.get(header_mapping["amount"])
        category = row.get(header_mapping["category"])
        description = row.get(header_mapping["description"])

        if not all([t_id, date_str, amount_str, category, description]):
            raise InvalidCSVException(f"Row {line_num}: Empty values are not allowed in required fields")

        try:
            amount = float(amount_str.strip())
        except ValueError as e:
            raise InvalidCSVException(f"Row {line_num}: Invalid amount '{amount_str}'. Must be a number.") from e

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
                "transaction_id": t_id.strip(),
                "date": parsed_date.isoformat(),
                "amount": amount,
                "category": category.strip(),
                "description": description.strip(),
            }
        )

    if not parsed_rows:
        raise InvalidCSVException("CSV file contains no data rows")

    return parsed_rows
