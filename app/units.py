import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction

SCALE = {"W": 1, "kW": 1000}
NUMBER = re.compile(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?")


def watts(value, unit):
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if unit not in SCALE or not NUMBER.fullmatch(text):
        raise ValueError("无效功率或单位")
    exact = Fraction(text.replace(",", "")) * SCALE[unit]
    if exact.denominator != 1 or exact > 10**9:
        raise ValueError("功率应为整瓦")
    return int(exact)


def demand_kw(watt_sum):
    return str((Decimal(watt_sum) / 3000).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
