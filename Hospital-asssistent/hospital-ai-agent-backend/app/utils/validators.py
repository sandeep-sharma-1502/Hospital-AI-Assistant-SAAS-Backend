# app/utils/validators.py

import re


def validate_phone_number(phone: str) -> str:
    """
    Validates Indian 10-digit phone number.
    - Removes spaces
    - Ensures only digits
    - Ensures length = 10
    """

    if not phone:
        raise ValueError("Phone number is required")

    # Remove spaces
    cleaned = phone.replace(" ", "")

    # Only digits allowed
    if not cleaned.isdigit():
        raise ValueError("Phone number must contain only digits")

    # Must be exactly 10 digits
    if len(cleaned) != 10:
        raise ValueError("Phone number must be exactly 10 digits")

    return cleaned