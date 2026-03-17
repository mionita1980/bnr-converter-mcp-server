#!/usr/bin/env python
#A MCP server offering conversions to RON, using the exchange rates from https://curs.bnr.ro/
from urllib.request import urlopen
import mcp.server.fastmcp
import logging
from functools import lru_cache
from datetime import date
from decimal import Decimal
import xml.etree.ElementTree as ET


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


BNR_NS = "http://www.bnr.ro/xsd"
BNR_URL_TEMPLATE = "https://curs.bnr.ro/files/xml/years/nbrfxrates{year}.xml"

mymcp = mcp.server.fastmcp.FastMCP("BNRServer")

@lru_cache(maxsize=16)
def _fetch_rates_for_year(year: int) -> list[tuple[date, dict[str, tuple[float, float]]]]:
    """Fetch and parse BNR exchange rates for a given year.

    Returns a sorted list of (date, {currency: (rate, multiplier)}) tuples.
    """
    url = BNR_URL_TEMPLATE.format(year=year)
    with urlopen(url, timeout=30) as resp:
        tree = ET.parse(resp)

    root = tree.getroot()
    entries: list[tuple[date, dict[str, tuple[float, float]]]] = []

    for cube in root.iter(f"{{{BNR_NS}}}Cube"):
        date_str = cube.get("date")
        if not date_str:
            continue
        cube_date = date.fromisoformat(date_str)
        rates: dict[str, tuple[float, float]] = {}
        for rate_el in cube.iter(f"{{{BNR_NS}}}Rate"):
            currency = rate_el.get("currency")
            multiplier = float(rate_el.get("multiplier", "1"))
            value = float(rate_el.text)
            rates[currency] = (value, multiplier)
        entries.append((cube_date, rates))

    entries.sort(key=lambda e: e[0])
    return entries

@mymcp.tool()
def _find_last_rate_before_bill_date(bill_date: date, currency: str) -> tuple[date, float]:
    """Find the last published BNR rate before bill date, for the given currency.

    Returns the rate date and value.
    """
    logger.debug(f"_find_last_rate_before_bill_date for bill date: {bill_date} and currency: {currency}")
    # We may need to look in the bill year and the previous year
    # (e.g. bill date is Jan 2 but no rates published yet that year).
    years_to_check = sorted({bill_date.year, bill_date.year - 1}, reverse=True)

    best_date: date | None = None
    best_rate: float = 0.0

    for year in years_to_check:
        try:
            entries = _fetch_rates_for_year(year)
        except Exception:
            continue

        for entry_date, rates in reversed(entries):
            if entry_date >= bill_date:
                continue
            if currency in rates:
                if best_date is None or entry_date > best_date:
                    logger.debug(f"Found rate: {rates[currency]}")
                    best_date = entry_date
                    rate_value, multiplier = rates[currency]
                    best_rate = float(Decimal(str(rate_value)) / Decimal(str(int(multiplier))))
                return (best_date, best_rate)

    if best_date is not None:
        logger.debug(f"Returning rate: {best_rate} from date: {best_date}")
        return (best_date, best_rate)

    logger.debug(f"No BNR rate found for bill date: {bill_date} and currency: {currency}")
    raise ValueError(
        f"No BNR rate found for {currency} on or before {bill_date.isoformat()}"
    )

@mymcp.tool()
def _find_last_rate_on_or_before_bill_date(bill_date: date, currency: str) -> tuple[date, float]:
    """Find the last published BNR rate on or before bill date, for the given currency.

    Returns the rate date and value.
    """
    logger.debug(f"_find_last_rate_on_or_before_bill_date for bill date: {bill_date} and currency: {currency}")
    # We may need to look in the bill year and the previous year
    # (e.g. bill date is Jan 2 but no rates published yet that year).
    years_to_check = sorted({bill_date.year, bill_date.year - 1}, reverse=True)

    best_date: date | None = None
    best_rate: float = 0.0

    for year in years_to_check:
        try:
            entries = _fetch_rates_for_year(year)
        except Exception:
            continue

        for entry_date, rates in reversed(entries):
            if entry_date > bill_date:
                continue
            if currency in rates:
                if best_date is None or entry_date > best_date:
                    logger.debug(f"Found rate: {rates[currency]}")
                    best_date = entry_date
                    rate_value, multiplier = rates[currency]
                    best_rate = float(Decimal(str(rate_value)) / Decimal(str(int(multiplier))))
                return (best_date, best_rate)

    if best_date is not None:
        logger.debug(f"Returning rate: {best_rate} from date: {best_date}")
        return (best_date, best_rate)

    logger.debug(f"No BNR rate found for bill date: {bill_date} and currency: {currency}")
    raise ValueError(
        f"No BNR rate found for {currency} on or before {bill_date.isoformat()}"
    )


@mymcp.tool()
def _convert_bill_to_RON_using_last_rate_before_bill_date(bill_amount: float, bill_date: date, currency: str) -> tuple[float, str]:
    """Convert the bill amount to RON, using the last published BNR rate before the bill date, for the given currency.

    Returns (amount_in_RON, description_string).
    """
    logger.debug(f"_convert_bill_to_RON_using_last_rate_before_bill_date for bill with amount: {bill_amount}, date: {bill_date} and currency: {currency}")
    rate_date, rate_value = _find_last_rate_before_bill_date(bill_date, currency)
    amount_in_ron = float(Decimal(str(bill_amount)) * Decimal(str(rate_value)))
    description = f"Converted {bill_amount} {currency} to {amount_in_ron} RON using rate {rate_value} from {rate_date}"
    logger.debug(description)
    return (amount_in_ron, description)

@mymcp.tool()
def _convert_bill_to_RON_using_last_rate_on_or_before_bill_date(bill_amount: float, bill_date: date, currency: str) -> tuple[float, str]:
    """Convert the bill amount to RON, using the last published BNR rate on or before the bill date, for the given currency.

    Returns (amount_in_RON, description_string).
    """
    logger.debug(f"_convert_bill_to_RON_using_last_rate_on_or_before_bill_date for bill with amount: {bill_amount}, date: {bill_date} and currency: {currency}")
    rate_date, rate_value = _find_last_rate_on_or_before_bill_date(bill_date, currency)
    amount_in_ron = float(Decimal(str(bill_amount)) * Decimal(str(rate_value)))
    description = f"Converted {bill_amount} {currency} to {amount_in_ron} RON using rate {rate_value} from {rate_date}"
    logger.debug(description)
    return (amount_in_ron, description)

def main():
    """Entry point for the BNR MCP server."""
    mymcp.run(transport="stdio")

if __name__ == "__main__":
    main()
