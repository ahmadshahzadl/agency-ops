"""Shared money-field validation for finance, quotes, and time billing."""
from decimal import Decimal
from fastapi import HTTPException, status


def validate_currency(currency: str | None) -> None:
    if currency is not None and (len(currency) != 3 or not currency.isalpha()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="currency must be a 3-letter code, e.g. USD")


def validate_positive_amount(amount: Decimal | None, field: str = "amount") -> None:
    if amount is not None and amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field} must be greater than 0")
