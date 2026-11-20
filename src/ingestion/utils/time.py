import re

_SPAN_PATTERN = re.compile(r"(\d+)([dm])")
MAX_MONTHS = 12
MAX_DAYS = 365


def parse_time_span(value: str) -> str:
    match = _SPAN_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("time span must use days or months, for example 10d or 3m")
    amount, unit = int(match.group(1)), match.group(2)
    if amount == 0:
        raise ValueError("time span must be greater than zero")
    if unit == "m" and amount > MAX_MONTHS:
        raise ValueError("time span cannot exceed 12 months")
    if unit == "d" and amount > MAX_DAYS:
        raise ValueError("time span cannot exceed 365 days")
    return value
