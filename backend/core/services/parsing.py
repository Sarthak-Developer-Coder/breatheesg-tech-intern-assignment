from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from dateutil import parser


_DECIMAL_CLEAN_RE = re.compile(r"[\s']+")


def parse_decimal(value: Any) -> Decimal | None:
    """Parse numbers that commonly appear in enterprise exports.

    Handles:
    - German decimal comma: "1.234,56"
    - US decimal point: "1,234.56"
    - Thousands separators, spaces, apostrophes
    - Parentheses for negative: "(123.4)"

    Returns None for empty/null inputs.
    """

    if value is None:
        return None

    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None

    raw = str(value).strip()
    if raw == '' or raw.lower() in {'null', 'none', 'nan'}:
        return None

    negative = False
    if raw.startswith('(') and raw.endswith(')'):
        negative = True
        raw = raw[1:-1].strip()

    raw = _DECIMAL_CLEAN_RE.sub('', raw)

    # Normalize decimal separator.
    if ',' in raw and '.' in raw:
        # Choose the last separator as decimal separator.
        if raw.rfind(',') > raw.rfind('.'):
            # 1.234,56 -> 1234.56
            raw = raw.replace('.', '')
            raw = raw.replace(',', '.')
        else:
            # 1,234.56 -> 1234.56
            raw = raw.replace(',', '')
    elif ',' in raw and '.' not in raw:
        # 1234,56 -> 1234.56
        raw = raw.replace(',', '.')

    try:
        num = Decimal(raw)
    except InvalidOperation:
        return None

    return -num if negative else num


def parse_date(value: Any) -> date | None:
    """Parse a date string from messy exports.

    Examples:
    - "31.12.2025" (German)
    - "2025/12/31"
    - "31-12-25"

    Returns None for empty/null inputs.
    """

    if value is None:
        return None

    raw = str(value).strip()
    if raw == '' or raw.lower() in {'null', 'none', 'nan'}:
        return None

    # Heuristic for day-first formats.
    dayfirst = '.' in raw or re.match(r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$", raw) is not None

    try:
        dt = parser.parse(raw, dayfirst=dayfirst, yearfirst=not dayfirst).date()
    except (ValueError, OverflowError):
        return None

    return dt


@dataclass(frozen=True)
class ParsedValue:
    value: Decimal
    unit: str
