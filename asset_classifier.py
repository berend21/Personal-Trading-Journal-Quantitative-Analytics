import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_CLASS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "asset_classes.csv"
)

ASSET_CLASSES = (
    "forex",
    "indices",
    "commodities",
    "crypto",
    "stocks",
    "unknown",
)


def load_asset_classes():
    classifications = {}

    if not os.path.exists(ASSET_CLASS_FILE):
        return classifications

    with open(
        ASSET_CLASS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file,
            delimiter=";"
        )

        if not reader.fieldnames:
            return classifications

        headers = {
            header.strip().lower(): header
            for header in reader.fieldnames
            if header
        }

        symbol_column = headers.get("symbol")
        asset_class_column = headers.get("asset_class")

        if not symbol_column or not asset_class_column:
            raise ValueError(
                "asset_classes.csv must contain "
                "'symbol' and 'asset_class' columns. "
                f"Found: {reader.fieldnames}"
            )

        for row in reader:
            symbol = (
                row.get(symbol_column) or ""
            ).strip().upper()

            asset_class = (
                row.get(asset_class_column) or ""
            ).strip().lower()

            if not symbol:
                continue

            if asset_class not in ASSET_CLASSES:
                asset_class = "unknown"

            classifications[symbol] = asset_class

    return classifications




def get_asset_class(symbol):
    symbol = (symbol or "").strip().upper()

    classifications = load_asset_classes()

    return classifications.get(
        symbol,
        "unknown"
    )
