"""
Unit-aware amount parsing and arithmetic for pantry / shopping amounts.

All amounts are stored as  "<qty> <unit>"  e.g. "500 g", "3 stk", "1.5 kg", "2 dl".

Supported units
---------------
  Amount family (1 g ≈ 1 ml — close enough for cooking):
      g, kg, dl, l, ts, ss

      base unit = g / ml (same number)
        g  →    1
        kg →  1 000
        dl →  100
        l  →  1 000
        ts →    5
        ss →   15

  Count family (separate, never mixes with amounts):
      stk

Any two amount-family units can be added or subtracted.
The result is displayed in the same unit-category as the first operand
(the pantry item), so grams stay grams, dl stays dl, etc.
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
# All "amount" units share one family; value = how many base-units (g/ml) per 1 unit.
_AMOUNT_UNITS = {
    'g':  Decimal('1'),
    'kg': Decimal('1000'),
    'dl': Decimal('100'),
    'l':  Decimal('1000'),
    'ts': Decimal('5'),
    'ss': Decimal('15'),
}

_COUNT_UNITS = {
    'stk': Decimal('1'),
}

# Flat lookup: unit_str -> (family_name, units_dict)
_UNIT_MAP: dict = {u: ('amount', _AMOUNT_UNITS) for u in _AMOUNT_UNITS}
_UNIT_MAP.update({u: ('count', _COUNT_UNITS) for u in _COUNT_UNITS})

# Which display-category each unit belongs to (for pretty output)
_DISPLAY_FAMILY = {
    'g': 'weight', 'kg': 'weight',
    'dl': 'volume', 'l': 'volume',
    'ts': 'spoon',  'ss': 'spoon',
    'stk': 'count',
}

# Aliases accepted in parse_amount (tolerates old free-text / typing variants)
_ALIASES = {
    'gram': 'g', 'grams': 'g',
    'kilogram': 'kg', 'kilograms': 'kg',
    'deciliter': 'dl', 'deciliters': 'dl', 'decilitre': 'dl',
    'liter': 'l', 'liters': 'l', 'litre': 'l', 'litres': 'l',
    'teskje': 'ts', 'teskjeer': 'ts', 'teaspoon': 'ts', 'tsp': 'ts',
    'spiseskje': 'ss', 'spiseskjeer': 'ss', 'tablespoon': 'ss', 'tbsp': 'ss',
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

    unit = _ALIASES.get(raw_unit, raw_unit)
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
        (Decimal('500'), 'g')   -> "500 g"
        (Decimal('1.5'), 'kg')  -> "1.5 kg"
        (Decimal('3'),   'stk') -> "3 stk"
    """
    qty = qty.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP).normalize()
    if qty == qty.to_integral_value():
        qty_str = str(int(qty))
    else:
        qty_str = str(qty)
    return f"{qty_str} {unit}"


def add_amounts(qty1: Decimal, unit1: str, qty2: Decimal, unit2: str):
    """
    Add two amounts.  Any two amount-family units work together.
    stk + anything else returns (None, None).

    The result is shown in the same unit-category as unit1 (the existing
    pantry item), so 500 g + 2 ss stays in grams.

    Examples:
        500 g  + 2 ss   = 530 g        (2 ss = 30 g)
        5 dl   + 3 ts   = 5.15 dl      (3 ts = 15 ml = 0.15 dl)
        500 g  + 3 dl   = 800 g        (3 dl = 300 ml ≈ 300 g)
        3 ts   + 3 ts   = 2 ss         (6 ts → divisible by 3 → ss)
    """
    return _combine(qty1, unit1, qty2, unit2, add=True)


def subtract_amounts(qty1: Decimal, unit1: str, qty2: Decimal, unit2: str):
    """
    Subtract qty2/unit2 from qty1/unit1.

    Returns (result_qty, result_unit).
    result_qty == 0 means "not enough left — delete the pantry item".
    Returns (None, None) only when units are truly incompatible (stk vs amount).

    Examples:
        500 g  - 8 ss   = 380 g        (8 ss = 120 g)
        10 dl  - 4 ts   = 9.8 dl       (4 ts = 20 ml = 0.2 dl)
        200 g  - 5 dl   = 0            (5 dl = 500 g > 200 g → delete)
    """
    return _combine(qty1, unit1, qty2, unit2, add=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _combine(qty1, unit1, qty2, unit2, *, add: bool):
    if unit1 not in _UNIT_MAP or unit2 not in _UNIT_MAP:
        return None, None

    fam1 = _UNIT_MAP[unit1][0]
    fam2 = _UNIT_MAP[unit2][0]

    if fam1 != fam2:
        return None, None  # stk mixed with an amount unit

    units = _UNIT_MAP[unit1][1]  # same dict for both since same family

    base1 = qty1 * units[unit1]
    base2 = qty2 * units[unit2]

    result_base = base1 + base2 if add else base1 - base2

    if not add and result_base <= 0:
        return Decimal('0'), unit1

    # Display in the same category as unit1 (the pantry item)
    return _pick_unit(result_base, unit1)


def _pick_unit(base_qty: Decimal, unit_hint: str):
    """
    Convert base_qty (in g/ml) to a human-friendly (qty, unit) pair.
    The display category (weight / volume / spoon) is taken from unit_hint.

    Weight  (g/kg):   >= 1 000 g  → kg,  else g
    Volume  (dl/l):   >= 1 000 ml → l,   else dl
    Spoon   (ts/ss):  divisible by 3 ts → ss, else ts
    Count   (stk):    always stk (base_qty already in stk)
    """
    cat = _DISPLAY_FAMILY.get(unit_hint, 'weight')

    if cat == 'weight':
        if base_qty >= 1000:
            return base_qty / 1000, 'kg'
        return base_qty, 'g'

    elif cat == 'volume':
        if base_qty >= 1000:
            return base_qty / 1000, 'l'
        return base_qty / 100, 'dl'

    elif cat == 'spoon':
        if base_qty % 3 == 0:
            return base_qty / 3, 'ss'
        return base_qty, 'ts'

    else:  # count
        return base_qty, 'stk'
