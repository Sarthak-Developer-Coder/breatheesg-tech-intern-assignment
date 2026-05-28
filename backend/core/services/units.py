from __future__ import annotations

from decimal import Decimal
from typing import Any


_UNIT_SYNONYMS: dict[str, str] = {
    # Volume
    'l': 'liter',
    'lt': 'liter',
    'ltr': 'liter',
    'liter': 'liter',
    'litre': 'liter',
    'liter.': 'liter',
    'liter(s)': 'liter',
    'liter\u00a0': 'liter',
    'liter. ': 'liter',
    'liter ': 'liter',
    'liters': 'liter',
    'litres': 'liter',
    'm3': 'm3',
    'm^3': 'm3',
    'cbm': 'm3',

    # Mass
    'kg': 'kg',
    'kilogram': 'kg',
    'kilogramm': 'kg',

    # Electricity
    'kwh': 'kWh',
    'kwh_total': 'kWh',
    'mwh': 'MWh',
    'wh': 'Wh',

    # Distance
    'km': 'km',

    # Lodging
    'night': 'night',
    'nights': 'night',
    'nacht': 'night',
    'naechte': 'night',
    'nächte': 'night',
}


def normalize_unit(raw_unit: Any) -> str | None:
    if raw_unit is None:
        return None

    unit = str(raw_unit).strip()
    if unit == '':
        return None

    unit_key = unit.lower().replace(' ', '').replace('\t', '')
    unit_key = unit_key.replace('(', '_').replace(')', '').replace('/', '_')

    if unit_key in _UNIT_SYNONYMS:
        return _UNIT_SYNONYMS[unit_key]

    # Preserve common canonical spellings.
    if unit in {'kWh', 'km', 'kg', 'MWh', 'Wh', 'liter', 'm3', 'night'}:
        return unit

    return None


def convert_quantity(quantity: Decimal, from_unit: str, to_unit: str) -> Decimal | None:
    if from_unit == to_unit:
        return quantity

    # Electricity conversions
    if from_unit == 'MWh' and to_unit == 'kWh':
        return quantity * Decimal('1000')
    if from_unit == 'Wh' and to_unit == 'kWh':
        return quantity / Decimal('1000')

    # Volume conversions
    if from_unit == 'm3' and to_unit == 'liter':
        return quantity * Decimal('1000')

    return None
