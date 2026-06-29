import pytest
from app.core.exceptions import InvalidCSVException
from app.utils.csv_parser import parse_and_validate_csv


def test_parse_valid_csv():
    valid_csv = (
        "transaction_id,date,amount,category,description,currency,account\n"
        "TX1001,2026-06-25,120.50,Groceries,Weekly grocery shop,INR,ACC01\n"
        "TX1002,06/26/2026,15.00,Coffee,Morning latte,USD,ACC02\n"
    )
    result = parse_and_validate_csv(valid_csv.encode("utf-8"))
    assert len(result) == 2
    assert result[0]["txn_id"] == "TX1001"
    assert result[0]["amount"] == 120.50
    assert result[0]["date"] == "2026-06-25"
    assert result[0]["merchant"] == "Weekly grocery shop"
    assert result[0]["currency"] == "INR"
    assert result[0]["account_id"] == "ACC01"

    assert result[1]["txn_id"] == "TX1002"
    assert result[1]["amount"] == 15.00
    assert result[1]["date"] == "2026-06-26"
    assert result[1]["merchant"] == "Morning latte"
    assert result[1]["currency"] == "USD"
    assert result[1]["account_id"] == "ACC02"


def test_parse_missing_headers():
    invalid_csv = (
        "txn_id,amount,category,description\n"
        "TX1001,120.50,Groceries,Weekly grocery shop\n"
    )
    with pytest.raises(InvalidCSVException) as exc_info:
        parse_and_validate_csv(invalid_csv.encode("utf-8"))
    assert "Missing required CSV columns" in str(exc_info.value)


def test_parse_invalid_amount():
    invalid_csv = (
        "txn_id,date,amount,merchant\nTX1001,2026-06-25,abc,Weekly grocery shop\n"
    )
    with pytest.raises(InvalidCSVException) as exc_info:
        parse_and_validate_csv(invalid_csv.encode("utf-8"))
    assert "Invalid amount" in str(exc_info.value)


def test_parse_invalid_date():
    invalid_csv = (
        "txn_id,date,amount,merchant\nTX1001,invalid-date,120.50,Weekly grocery shop\n"
    )
    with pytest.raises(InvalidCSVException) as exc_info:
        parse_and_validate_csv(invalid_csv.encode("utf-8"))
    assert "Invalid date format" in str(exc_info.value)
