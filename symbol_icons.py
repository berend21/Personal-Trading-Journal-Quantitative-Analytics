import os
import re

from asset_classifier import get_asset_class


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSET_ICON_DIR = os.path.join(
    BASE_DIR,
    "static",
    "icons",
    "assets",
)

FLAG_ICON_DIR = os.path.join(
    BASE_DIR,
    "static",
    "icons",
    "flags",
)


# Currency → flag filename
CURRENCY_FLAGS = {
    "EUR": "eu",
    "USD": "us",
    "GBP": "gb",
    "JPY": "jp",
    "CHF": "ch",
    "AUD": "au",
    "NZD": "nz",
    "CAD": "ca",
    "SEK": "se",
    "NOK": "no",
    "DKK": "dk",
    "SGD": "sg",
    "HKD": "hk",
    "ZAR": "za",
    "MXN": "mx",
    "TRY": "tr",
    "PLN": "pl",
    "CZK": "cz",
    "HUF": "hu",
}


def normalize_symbol(symbol):

    symbol = (symbol or "").strip().upper()

    if ":" in symbol:
        symbol = symbol.split(":")[-1]

    if symbol.endswith("=X"):
        symbol = symbol[:-2]

    symbol = re.sub(r"[^A-Z0-9]", "", symbol)

    return symbol.lower()


def get_forex_currencies(symbol):

    normalized = normalize_symbol(symbol).upper()

    if len(normalized) != 6:
        return None

    base = normalized[:3]
    quote = normalized[3:]

    if base not in CURRENCY_FLAGS:
        return None

    if quote not in CURRENCY_FLAGS:
        return None

    return base, quote


def get_asset_icon(symbol):

    filename = normalize_symbol(symbol)

    for extension in ("svg", "png", "webp"):
        path = os.path.join(
            ASSET_ICON_DIR,
            f"{filename}.{extension}",
        )

        if os.path.isfile(path):
            return f"/static/icons/assets/{filename}.{extension}"

    return None


def get_flag_icon(currency):

    filename = CURRENCY_FLAGS.get(currency)

    if not filename:
        return None

    for extension in ("svg", "png", "webp"):
        path = os.path.join(
            FLAG_ICON_DIR,
            f"{filename}.{extension}",
        )

        if os.path.isfile(path):
            return f"/static/icons/flags/{filename}.{extension}"

    return None


def get_symbol_icon(symbol):

    normalized = normalize_symbol(symbol)

    asset_class = get_asset_class(normalized.upper())

    # FOREX
    if asset_class == "forex":

        currencies = get_forex_currencies(normalized)

        if currencies:
            base, quote = currencies

            return {
                "type": "forex",
                "symbol": normalized,
                "base": get_flag_icon(base),
                "quote": get_flag_icon(quote),
                "asset_class": asset_class,
            }

        return {
            "type": "fallback",
            "symbol": normalized,
            "asset_class": asset_class,
        }


    icon = get_asset_icon(normalized)

    if icon:
        return {
            "type": "asset",
            "symbol": normalized,
            "asset_class": asset_class,
            "icon": icon,
        }
    # NO ICON

    return {
        "type": "fallback",
        "symbol": normalized,
        "asset_class": asset_class,
    }
