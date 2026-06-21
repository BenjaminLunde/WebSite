"""
Unit-aware amount parsing and arithmetic for pantry / shopping amounts.

All amounts are stored as  "<qty> <unit>"  e.g. "500 g", "3 stk", "1.5 kg", "2 dl".

Supported units
---------------
  Weight : g, kg          (base: g  — 1 kg = 1 000 g)
  Volume : ts, ss, dl, l  (base: ml — 1 ts = 5 ml, 1 ss = 15 ml,
                                      1 dl = 100 ml, 1 l = 1 000 ml)
  Count  : stk            (no conversion)

Cross-unit arithmetic is possible within the same family (e.g. dl + l, ts + dl).
Cross-family arithmetic (e.g. g + dl) returns (None, None) — incompatible.
"""

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Public constant — drives the unit dropdown in templates
# ---------------------------------------------------------------------------
UNITS = ['g', 'kg', 'dl', 'l', 'ts', 'ss', 'stk']

# ---------------------------------------------------------------------------
# Internal lookup tables
# ---------------------------------------------------------------------------
# Each value is the multiplier to convert 1 <unit> → base unit.
_FAMILIES = {
    'weight': {
        'g':  Decimal('1'),
        'kg': Decimal('1000'),
    },
    'volume': {
        # base unit = ml
        'ts': Decimal('5'),      # teskje  = 5 ml
        'ss': Decimal('15'),     # spiseskje = 15 ml
        'dl': Decimal('100'),    # deciliter = 100 ml
        'l':  Decimal('1000'),   # liter = 1 000 ml
    },
    'count': {
        'stk': Decimal('1'),
    },
}

# Flat lookup: unit_str -> (family_name, units_dict)
_UNIT_MAP: dict = {}
for _fam, _units in _FAMILIES.items():
    for _u in _units:
        _UNIT_MAP[_u] = (_fam, _units)

# Aliases accepted in parse_amount (tolerates old free-text values / typos)
_ALIASES = {
    # weight
    'gram': 'g', 'grams': 'g',
    'kilogram': 'kg', 'kilograms': 'kg',
    # volume
    'teskje': 'ts', 'teskjeer': 'ts', 'teaspoon': 'ts', 'tsp': 'ts',
    'spiseskje': 'ss', 'spiseskjeer': 'ss', 'tablespoon': 'ss', 'tbsp': 'ss',
    'deciliter': 'dl', 'deciliters': 'dl', 'decilitre': 'dl',
    'liter': 'l', 'liters': 'l', 'litre': 'l', 'litres': 'l',
    # count
    'pcs': 'stk', 'pc': 'stk', 'piece': 'stk', 'pieces': 'stk',
    'stykk': 'stk', 'stykker': 'stk',
}

_PARSE_RE = re.compile(r'^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]*)\s*$')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_amount(text: str):
    """
    Parse a stored amount string into (Decimal, unit_str).

    Returns (None, None) if the text cannot be parsed or the unit is
    unrecognised — callers must handle this gracefully.

    Examples:
        "500 g"   -> (Decimal('500'), 'g')
        "1.5 kg"  -> (Decimal('1.5'), 'kg')
        "2 ts"    -> (Decimal('2'), 'ts')
        "3 stk"   -> (Decimal('3'), 'stk')
        "2 cups"  -> (None, None)    # unrecognised unit
    """
    if not text:
        return None, None
    m = _PARSE_RE.match(text.strip())
    if not m:
        return None, None
    qty_str = m.group(1).replace(',', '.')
    raw_unit = m.group(2).strip().lower()

    # Resolve aliases first
    unit = _ALIASES.get(raw_unit, raw_unit)

    # A bare number with no unit is treated as pieces
    if unit == '':
        unit = 'stk'

    if unit not in _UNIT_MAP:
        return None, None

    try:
        qty = Decimal(qty_str)
    except InvalidOperation:
        return None, None

    return qty, unit


def format_amount(qty: Decimal, unit: str) -> str:
    """
    Format a (qty, unit) pair to a display/storage string.

    Keeps at most 2 decimal places; drops trailing zeros.

    Examples:
        (Decimal('500'), 'g')    -> "500 g"
        (Decimal('1.5'), 'kg')   -> "1.5 kg"
        (Decimal('3'),   'stk')  -> "3 stk"
        (Decimal('0.5'), 'l')    -> "0.5 l"
    """
    qty = qty.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP).normalize()
    if qty == qty.to_integral_value():
        qty_str = str(int(qty))
    else:
        qty_str = str(qty)
    return f"{qty_str} {unit}"


def add_amounts(qty1: Decimal, unit1: str, qty2: Decimal, unit2: str):
    """
    Add two amounts, converting between units in the same family.

    Returns (result_qty, result_unit), or (None, None) if the units are
    from different families (e.g. g + dl).

    Auto-promotes to a larger unit when the result is large enough:
        700 g  + 500 g  = 1.2 kg
        8 dl   + 5 dl   = 1.3 l
        2 ts   + 4 ts   = 30 ml  = 2 ss
        3 ss   + 2 dl   = 245 ml = 2.45 dl
    """
    return _combine(qty1, unit1, qty2, unit2, add=True)


def subtract_amounts(qty1: Decimal, unit1: str, qty2: Decimal, unit2: str):
    """
    Subtract qty2/unit2 from qty1/unit1.

    Returns (result_qty, result_unit).
    If the result is ≤ 0, result_qty is Decimal('0') — the caller should
    treat this as "delete the pantry item".
    Returns (None, None) if units are from different families.

    Example:
        2 dl  - 0.5 l  -> (0, 'dl')  [not enough — delete]
        10 dl - 0.5 l  -> (500 ml)   -> (5, 'dl')
    """
    return _combine(qty1, unit1, qty2, unit2, add=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _combine(qty1, unit1, qty2, unit2, *, add: bool):
    """Shared logic for add / subtract with automatic unit conversion."""
    if unit1 not in _UNIT_MAP or unit2 not in _UNIT_MAP:
        return None, None

    fam1, units1 = _UNIT_MAP[unit1]
    fam2, units2 = _UNIT_MAP[unit2]

    if fam1 != fam2:
        return None, None  # incompatible families (e.g. g + dl)

    # Convert both operands to the family's base unit
    base1 = qty1 * units1[unit1]
    base2 = qty2 * units2[unit2]

    result_base = base1 + base2 if add else base1 - base2

    if not add and result_base <= 0:
        return Decimal('0'), unit1  # signal to caller: delete the pantry item

    return _pick_unit(result_base, fam1)


def _pick_unit(base_qty: Decimal, family: str):
    """
    Choose a human-friendly display unit for a result expressed in base units.

    Weight (base = g):
        >= 1 000 g  →  kg
        else        →  g

    Volume (base = ml):
        >= 1 000 ml →  l
        >=   100 ml →  dl
        >=    15 ml →  ss
        <     15 ml →  ts

    Count (base = stk):
        always stk
    """
    if family == 'weight':
        if base_qty >= 1000:
            return base_qty / 1000, 'kg'
        return base_qty, 'g'

    elif family == 'volume':
        if base_qty >= 1000:
            return base_qty / 1000, 'l'
        if base_qty >= 100:
            return base_qty / 100, 'dl'
        if base_qty >= 15:
            return base_qty / 15, 'ss'
        return base_qty / 5, 'ts'

    else:  # count
        return base_qty, 'stk'
