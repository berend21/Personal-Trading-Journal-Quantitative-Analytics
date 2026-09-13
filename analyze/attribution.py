from asset_classifier import get_asset_class, ASSET_CLASSES
from analyze.statistics import (calculate_win_rate,calculate_profit_factor, safe_float)


def calculate_asset_class_stats(rows):
    stats = {
        asset_class: {
            "trade_count": 0,
            "closed_count": 0,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "total_rr": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
        }
        for asset_class in ASSET_CLASSES
    }

    for row in rows:
        symbol = (row["symbol"] or "").strip().upper()
        asset_class = get_asset_class(symbol)

        if asset_class not in stats:
            stats[asset_class] = {
                "trade_count": 0,
                "closed_count": 0,
                "wins": 0,
                "losses": 0,
                "breakevens": 0,
                "total_rr": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
            }

        data = stats[asset_class]
        data["trade_count"] += 1

        if row["status"] != "CLOSED" or row["RR"] is None:
            continue

        rr = safe_float(row["RR"])

        data["closed_count"] += 1
        data["total_rr"] += rr

        if rr > 0:
            data["wins"] += 1
            data["gross_profit"] += rr

        elif rr < 0:
            data["losses"] += 1
            data["gross_loss"] += abs(rr)

        else:
            data["breakevens"] += 1

    for data in stats.values():

        closed_count = data["closed_count"]

        data["win_rate"] = calculate_win_rate(
            data["wins"],
            closed_count,
        )

        data["average_rr"] = (
            data["total_rr"] / closed_count
            if closed_count
            else 0.0
        )

        data["profit_factor"] = calculate_profit_factor(
            data["gross_profit"],
            data["gross_loss"],
        )

    return stats
