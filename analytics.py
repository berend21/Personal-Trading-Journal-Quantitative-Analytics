from flask import render_template, request
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta
import math
from asset_classifier import get_asset_class, ASSET_CLASSES

VALID_PERIODS = {"monthly", "last_month", "7d", "30d","90d","ytd","all","custom"}
VALID_ATTRIBUTIONS = {"entry", "exit"}
TRADE_TYPES = ("HTF", "MTF", "LTF")
DIRECTIONS = ("LONG", "SHORT")

from statistics import (
    safe_float,
    roundit,
    percentage,
    calculate_streaks,
    calculate_drawdown,
)


def _date_range(
    period,
    now,
    custom_start=None,
    custom_end=None,
):
    today_end = now.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )

    if period == "7d":
        start = (now - timedelta(days=6)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "30d":
        start = (now - timedelta(days=29)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "90d":
        start = (now - timedelta(days=89)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return start, today_end

    if period == "monthly":
        start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start, today_end


    if period == "last_month":
        this_month_start = now.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        last_month_end = (
            this_month_start - timedelta(microseconds=1)
        )

        last_month_start = last_month_end.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return last_month_start, last_month_end

    if period == "ytd":
        start = now.replace(
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        return start, today_end

    if period == "custom":
        return custom_start, custom_end

    # all
    return None, None



def _build_filter(
    period,
    now,
    date_field="close_time",
    custom_start=None,
    custom_end=None,
):

    if date_field not in {"open_time", "close_time"}:
        raise ValueError(
            f"Invalid analytics date field: {date_field}"
        )

    conditions = ["parent_id IS NULL"]
    params = []

    start_date, end_date = _date_range(
        period,
        now,
        custom_start=custom_start,
        custom_end=custom_end,
    )

    if start_date and end_date:
        conditions.append(
            f"{date_field} >= ? AND {date_field} <= ?"
        )

        params.extend([
            start_date.strftime("%Y-%m-%d %H:%M:%S"),
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    return " AND ".join(conditions), params





def _calculate_asset_class_stats(rows):
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

    for asset_class, data in stats.items():
        closed_count = data["closed_count"]

        data["win_rate"] = percentage(
            data["wins"],
            closed_count,
        )

        data["average_rr"] = (
            round(data["total_rr"] / closed_count, 2)
            if closed_count
            else 0.0
        )

        data["profit_factor"] = (
            round(
                data["gross_profit"] /
                data["gross_loss"],
                2,
            )
            if data["gross_loss"] > 0
            else None
        )

        data["total_rr"] = round(data["total_rr"], 2)

    return stats


@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics():

    period = request.args.get("period", "monthly")

    if period not in VALID_PERIODS:
        period = "monthly"

    attribution = request.args.get("attribution", "exit")

    if attribution not in VALID_ATTRIBUTIONS:
        attribution = "exit"

    custom_start = None
    custom_end = None

    if period == "custom":

        custom_start_raw = request.args.get("start")
        custom_end_raw = request.args.get("end")

        try:
            if not custom_start_raw or not custom_end_raw:
                raise ValueError("Custom start and end dates are required")

            custom_start = datetime.strptime(
                custom_start_raw,
                "%Y-%m-%d",
            ).replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

            custom_end = datetime.strptime(
                custom_end_raw,
                "%Y-%m-%d",
            ).replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=999999,
            )

            if custom_end < custom_start:
                raise ValueError(
                    "Custom end date cannot be before start date"
                )

        except (TypeError, ValueError):
            return "Invalid custom date range", 400


    now = datetime.now()
    
    

    conn = get_db()


    display_start, display_end = _date_range(
        period,
        now,
        custom_start=custom_start,
        custom_end=custom_end,
    )

    if period == "all":

        date_range_row = conn.execute(
            """
            SELECT
                MIN(open_time) AS first_date,
                MAX(close_time) AS last_date
            FROM trades
            WHERE parent_id IS NULL
            """
        ).fetchone()

        display_start = date_range_row["first_date"]
        display_end = date_range_row["last_date"]


    date_range_label = None

    if display_start and display_end:

        if isinstance(display_start, str):
            display_start = datetime.fromisoformat(
                display_start
            )

        if isinstance(display_end, str):
            display_end = datetime.fromisoformat(
                display_end
            )

        date_range_label = (
            f"{display_start.strftime('%d %B %Y')} "
            f"– "
            f"{display_end.strftime('%d %B %Y')}"
        )




    performance_where, performance_params = _build_filter(
        period,
        now,
        date_field="close_time",
        custom_start=custom_start,
        custom_end=custom_end,
    )

    entry_where, entry_params = _build_filter(
        period,
        now,
        date_field="open_time",
        custom_start=custom_start,
        custom_end=custom_end,
    )

    entry_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {entry_where}
        """,
        entry_params,
    ).fetchone()[0] or 0



    asset_class_rows = conn.execute(
        f"""
        SELECT
            symbol,
            status,
            RR
        FROM trades
        WHERE {performance_where}
        """,
        performance_params,
    ).fetchall()

    asset_class_stats = _calculate_asset_class_stats(
        asset_class_rows
    )
    


    total_trades = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {entry_where}
        """,
        entry_params,
    ).fetchone()[0] or 0


    open_trades = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {entry_where}
        AND status = 'OPEN'
        """,
        entry_params,
    ).fetchone()[0] or 0

    overview_closed_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {entry_where}
        AND status = 'CLOSED'
        """,
        entry_params,
    ).fetchone()[0] or 0
    status_rows = conn.execute(
        f"""
        SELECT status, COUNT(*) AS count
        FROM trades
        WHERE {entry_where}
        GROUP BY status
        ORDER BY status
        """,
        entry_params,
    ).fetchall()


    closed_raw = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total,

            SUM(
                CASE
                    WHEN RR > 0 THEN 1
                    ELSE 0
                END
            ) AS wins,

            SUM(
                CASE
                    WHEN RR = 0 THEN 1
                    ELSE 0
                END
            ) AS breakevens,

            SUM(
                CASE
                    WHEN RR < 0 THEN 1
                    ELSE 0
                END
            ) AS losses,

            SUM(RR) AS total_rr,
            AVG(RR) AS average_rr,

            MAX(RR) AS best_rr,
            MIN(RR) AS worst_rr,

            AVG(
                CASE
                    WHEN RR > 0 THEN RR
                END
            ) AS average_win,

            AVG(
                CASE
                    WHEN RR < 0 THEN RR
                END
            ) AS average_loss,

            SUM(
                CASE
                    WHEN RR > 0 THEN RR
                    ELSE 0
                END
            ) AS gross_profit,

            SUM(
                CASE
                    WHEN RR < 0 THEN ABS(RR)
                    ELSE 0
                END
            ) AS gross_loss,

            COUNT(
                CASE
                    WHEN RR IS NOT NULL THEN 1
                END
            ) AS valid_rr_count

        FROM trades
        WHERE {performance_where}
          AND status = 'CLOSED'
          AND RR IS NOT NULL
        """,
        performance_params,
    ).fetchone()

    closed_count = int(closed_raw["total"] or 0)
    win_count = int(closed_raw["wins"] or 0)
    loss_count = int(closed_raw["losses"] or 0)
    breakeven_count = int(closed_raw["breakevens"] or 0)

    total_rr = roundit(closed_raw["total_rr"])
    average_rr = roundit(closed_raw["average_rr"])

    average_win = roundit(closed_raw["average_win"])
    average_loss = roundit(closed_raw["average_loss"])

    highest_rr = (
        roundit(closed_raw["best_rr"])
        if closed_raw["best_rr"] is not None
        else None
    )

    lowest_rr = (
        roundit(closed_raw["worst_rr"])
        if closed_raw["worst_rr"] is not None
        else None
    )

    gross_profit = roundit(closed_raw["gross_profit"])
    gross_loss = roundit(closed_raw["gross_loss"])

    win_rate = percentage(win_count, closed_count)

    loss_rate = percentage(loss_count, closed_count)

    breakeven_rate = percentage(
        breakeven_count,
        closed_count,
    )

    # Expectancy = average R per closed trade.
    # E = (Win rate × Average Win)
    #     + (Loss rate × Average Loss)
 
    expectancy = average_rr

    profit_factor = (
        round(gross_profit / gross_loss, 2)
        if gross_loss > 0
        else None
    )

    payoff_ratio = (
        round(average_win / abs(average_loss), 2)
        if average_loss < 0
        else None
    )

    median_row = conn.execute(
        f"""
        WITH ranked AS (
            SELECT
                RR,
                ROW_NUMBER() OVER (ORDER BY RR) AS rn,
                COUNT(*) OVER () AS cnt
            FROM trades
            WHERE {performance_where}
              AND status = 'CLOSED'
              AND RR IS NOT NULL
        )
        SELECT AVG(RR) AS median_rr
        FROM ranked
        WHERE rn IN (
            CAST((cnt + 1) / 2 AS INTEGER),
            CAST((cnt + 2) / 2 AS INTEGER)
        )
        """,
        performance_params,
    ).fetchone()

    median_rr = (
        roundit(median_row["median_rr"])
        if median_row and median_row["median_rr"] is not None
        else None
    )

    rr_rows = conn.execute(
        f"""
        SELECT RR
        FROM trades
        WHERE {performance_where}
        AND status = 'CLOSED'
        AND RR IS NOT NULL
        ORDER BY close_time ASC, id ASC
        """,
        performance_params,
    ).fetchall()


    rr_sequence = [
        safe_float(row["RR"])
        for row in rr_rows
    ]

    rr_stddev = 0.0

    if len(rr_sequence) > 1:
        mean = sum(rr_sequence) / len(rr_sequence)

        variance = sum(
            (x - mean) ** 2
            for x in rr_sequence
        ) / (len(rr_sequence) - 1)

        rr_stddev = math.sqrt(variance)

    rr_stddev = round(rr_stddev, 2)

    max_win_streak, max_loss_streak = calculate_streaks(
        rr_sequence
    )

    (
        max_drawdown,
        max_drawdown_pct,
        equity_curve,
        drawdown_curve,
    ) = calculate_drawdown(rr_sequence)


    ticker_row = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS trade_count
        FROM trades
        WHERE {performance_where}
          AND symbol IS NOT NULL
          AND TRIM(symbol) != ''
        GROUP BY symbol
        ORDER BY trade_count DESC, symbol ASC
        LIMIT 1
        """,
        performance_params,
    ).fetchone()

    most_used_ticker = (
        ticker_row["symbol"]
        if ticker_row
        else "N/A"
    )

    direction_rows = conn.execute(
        f"""
        SELECT
            sort,
            COUNT(*) AS total,

            SUM(
                CASE
                    WHEN status = 'CLOSED'
                    AND RR IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS closed_count,

            SUM(
                CASE
                    WHEN status = 'CLOSED'
                    AND RR > 0
                    THEN 1
                    ELSE 0
                END
            ) AS wins,

            SUM(
                CASE
                    WHEN status = 'CLOSED'
                    AND RR IS NOT NULL
                    THEN RR
                    ELSE 0
                END
            ) AS total_rr

        FROM trades
        WHERE {performance_where}
        AND sort IN ('LONG', 'SHORT')
        GROUP BY sort
        """,
        performance_params,
    ).fetchall()


    direction_stats = {
        direction: {
            "count": 0,
            "closed_count": 0,
            "wins": 0,
            "win_rate": 0.0,
            "total_rr": 0.0,
        }
        for direction in DIRECTIONS
    }

    for row in direction_rows:
        direction = row["sort"]

        if direction not in direction_stats:
            continue

        count = int(row["total"] or 0)
        closed_count = int(row["closed_count"] or 0)
        wins = int(row["wins"] or 0)

        direction_stats[direction] = {
            "count": count,
            "closed_count": closed_count,
            "wins": wins,
            "win_rate": percentage(wins, closed_count),
            "total_rr": roundit(row["total_rr"]),
        }



    long_count = direction_stats["LONG"]["count"]
    short_count = direction_stats["SHORT"]["count"]

    total_direction_trades = long_count + short_count

    long_ratio = percentage(
        long_count,
        total_direction_trades,
    )

    short_ratio = percentage(
        short_count,
        total_direction_trades,
    )


    trades_per_type_rows = conn.execute(
        f"""
        SELECT
            type,
            COUNT(*) AS total
        FROM trades
        WHERE {performance_where}
        GROUP BY type
        """,
        performance_params,
    ).fetchall()

    trades_per_type = {
        row["type"]: int(row["total"] or 0)
        for row in trades_per_type_rows
    }

    trades_per_type_complete = {
        trade_type: trades_per_type.get(trade_type, 0)
        for trade_type in TRADE_TYPES
    }

    type_stats = {}

    for trade_type in TRADE_TYPES:

        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN RR > 0 THEN 1
                        ELSE 0
                    END
                ) AS wins,

                SUM(
                    CASE
                        WHEN RR < 0 THEN 1
                        ELSE 0
                    END
                ) AS losses,

                SUM(
                    CASE
                        WHEN RR = 0 THEN 1
                        ELSE 0
                    END
                ) AS breakevens,

                SUM(RR) AS total_rr,
                AVG(RR) AS average_rr

            FROM trades

            WHERE {performance_where}
            AND type = ?
            AND status = 'CLOSED'
            AND RR IS NOT NULL
            """,
            performance_params + [trade_type],
        ).fetchone()


        total = int(row["total"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        breakevens = int(row["breakevens"] or 0)

        type_stats[trade_type] = {
            "closed_count": total,
            "win_count": wins,
            "loss_count": losses,
            "breakeven_count": breakevens,
            "win_rate": percentage(wins, total),
            "total_rr": roundit(row["total_rr"]),
            "average_rr": roundit(row["average_rr"]),
        }


    long_short_per_type = {
        trade_type: {
            "long_count": 0,
            "short_count": 0,
        }
        for trade_type in TRADE_TYPES
    }

    rows = conn.execute(
        f"""
        SELECT
            type,
            sort,
            COUNT(*) AS total
        FROM trades
        WHERE {performance_where}
          AND sort IN ('LONG', 'SHORT')
        GROUP BY type, sort
        """,
        performance_params,
    ).fetchall()

    for row in rows:

        trade_type = row["type"]
        direction = row["sort"]

        if trade_type not in long_short_per_type:
            continue

        if direction == "LONG":
            long_short_per_type[trade_type]["long_count"] = int(
                row["total"] or 0
            )

        elif direction == "SHORT":
            long_short_per_type[trade_type]["short_count"] = int(
                row["total"] or 0
            )

    total_rr_per_type = {
        trade_type: type_stats[trade_type]["total_rr"]
        for trade_type in TRADE_TYPES
    }

    duration_row = conn.execute(
        f"""
        SELECT
            AVG(
                julianday(close_time) -
                julianday(open_time)
            ) * 86400 AS avg_seconds

        FROM trades

        WHERE {performance_where}
          AND status = 'CLOSED'
          AND open_time IS NOT NULL
          AND close_time IS NOT NULL
        """,
        performance_params,
    ).fetchone()

    avg_duration_seconds = safe_float(
        duration_row["avg_seconds"]
        if duration_row
        else 0
    )

    avg_trade_duration_days = round(
        avg_duration_seconds / 86400,
        1,
    )

    avg_trade_duration_hours = round(
        avg_duration_seconds / 3600,
        2,
    )

    daily_rows = conn.execute(
        f"""
        SELECT
            DATE(close_time) AS trade_date,
            SUM(RR) AS total_rr,
            COUNT(*) AS trade_count

        FROM trades

        WHERE {performance_where}
          AND status = 'CLOSED'
          AND RR IS NOT NULL
          AND close_time IS NOT NULL

        GROUP BY DATE(close_time)
        ORDER BY trade_date ASC
        """,
        performance_params,
    ).fetchall()

    daily_performance = []

    for row in daily_rows:
        daily_performance.append({
            "date": row["trade_date"],
            "rr": roundit(row["total_rr"]),
            "trade_count": int(row["trade_count"] or 0),
        })

    best_day = max(
        daily_performance,
        key=lambda x: x["rr"],
        default=None,
    )

    worst_day = min(
        daily_performance,
        key=lambda x: x["rr"],
        default=None,
    )


    symbol_rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS trade_count,

            SUM(
                CASE
                    WHEN RR > 0 THEN 1
                    ELSE 0
                END
            ) AS wins,

            SUM(
                CASE
                    WHEN RR < 0 THEN 1
                    ELSE 0
                END
            ) AS losses,

            SUM(
                CASE
                    WHEN RR = 0 THEN 1
                    ELSE 0
                END
            ) AS breakevens,

            SUM(RR) AS total_rr,
            AVG(RR) AS average_rr

        FROM trades

        WHERE {performance_where}
        AND status = 'CLOSED'
        AND RR IS NOT NULL
        AND symbol IS NOT NULL
        AND TRIM(symbol) != ''

        GROUP BY symbol

        ORDER BY total_rr DESC
        """,
        performance_params,
    ).fetchall()


    symbol_stats = []

    for row in symbol_rows:
        count = int(row["trade_count"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        breakevens = int(row["breakevens"] or 0)

        symbol_stats.append({
            "symbol": row["symbol"],
            "trade_count": count,
            "wins": wins,
            "losses": losses,
            "breakevens": breakevens,
            "win_rate": percentage(wins, count),
            "total_rr": roundit(row["total_rr"]),
            "average_rr": roundit(row["average_rr"]),
        })


    rr_labels = []
    rr_values = []

    if period in {"7d", "30d", "monthly", "last_month", "custom"}:

        rr_labels = [
            row["date"]
            for row in daily_performance
        ]

        rr_values = [
            row["rr"]
            for row in daily_performance
        ]

    elif period in {"90d"}:

        # Keep the chart readable by aggregating into weeks.
        weekly_rows = conn.execute(
            f"""
            SELECT
                DATE(
                    close_time,
                    '-' || ((CAST(strftime('%w', close_time) AS INTEGER) + 6) % 7) || ' days'
                ) AS week_start,
                SUM(RR) AS total_rr

            FROM trades

            WHERE {performance_where}
            AND status = 'CLOSED'
            AND RR IS NOT NULL
            AND close_time IS NOT NULL

            GROUP BY week_start
            ORDER BY week_start
            """,
            performance_params,
        ).fetchall()

        rr_labels = [
            row["week_start"]
            for row in weekly_rows
        ]

        rr_values = [
            roundit(row["total_rr"])
            for row in weekly_rows
        ]

    elif period in {"ytd", "all"}:

        monthly_rows = conn.execute(
            f"""
            SELECT
                strftime('%Y-%m', close_time) AS month,
                SUM(RR) AS total_rr

            FROM trades

            WHERE {performance_where}
            AND status = 'CLOSED'
            AND RR IS NOT NULL
            AND close_time IS NOT NULL

            GROUP BY strftime('%Y-%m', close_time)
            ORDER BY month
            """,
            performance_params,
        ).fetchall()

        rr_labels = [
            row["month"]
            for row in monthly_rows
        ]

        rr_values = [
            roundit(row["total_rr"])
            for row in monthly_rows
        ]

    else:

        recent_days = daily_performance[-30:]

        rr_labels = [
            row["date"]
            for row in recent_days
        ]

        rr_values = [
            row["rr"]
            for row in recent_days
        ]


    equity_chart_values = equity_curve

    drawdown_chart_values = drawdown_curve


    r_multiple_efficiency = (
        round(total_rr / closed_count, 2)
        if closed_count > 0
        else 0.0
    )

    positive_expectancy = expectancy > 0

    missing_rr_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {performance_where}
          AND status = 'CLOSED'
          AND RR IS NULL
        """,
        performance_params,
    ).fetchone()[0] or 0

    missing_close_time_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {performance_where}
          AND status = 'CLOSED'
          AND close_time IS NULL
        """,
        performance_params,
    ).fetchone()[0] or 0


    analytics_data = {

        "total_trades": int(total_trades),
        "entry_count" : int(entry_count),
        "closed_count": int(overview_closed_count),
        "open_count": int(open_trades),

        "win_count": int(win_count),
        "loss_count": int(loss_count),
        "breakeven_count": int(breakeven_count),

        "win_rate": float(win_rate),
        "loss_rate": float(loss_rate),
        "breakeven_rate": float(breakeven_rate),

        "total_rr": float(total_rr),
        "average_rr": float(average_rr),
        "median_rr": median_rr,

        "expectancy": float(expectancy),

        "highest_rr": (
            float(highest_rr)
            if highest_rr is not None
            else None
        ),

        "lowest_rr": (
            float(lowest_rr)
            if lowest_rr is not None
            else None
        ),

        "average_win": float(average_win),
        "average_loss": float(average_loss),

        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),

        "profit_factor": profit_factor,
        "payoff_ratio": payoff_ratio,

        "rr_stddev": float(rr_stddev),

        "max_drawdown": float(max_drawdown),
        "max_drawdown_pct": float(max_drawdown_pct),

        "max_win_streak": int(max_win_streak),
        "max_loss_streak": int(max_loss_streak),

        "r_multiple_efficiency": float(
            r_multiple_efficiency
        ),

        "positive_expectancy": bool(
            positive_expectancy
        ),

        "long_count": int(long_count),
        "short_count": int(short_count),

        "long_ratio": float(long_ratio),
        "short_ratio": float(short_ratio),

        "direction_stats": direction_stats,

        "most_used_ticker": most_used_ticker,
        "symbol_stats": symbol_stats,

        "asset_class_stats": asset_class_stats,


        "avg_trade_duration": float(
            avg_trade_duration_days
        ),

        "avg_trade_duration_hours": float(
            avg_trade_duration_hours
        ),

        "trades_per_type": trades_per_type_complete,
        "type_stats": type_stats,

        "long_short_per_type": long_short_per_type,
        "total_rr_per_type": total_rr_per_type,

        "best_day": best_day,
        "worst_day": worst_day,
        "daily_performance": daily_performance,

        "rr_labels": rr_labels,
        "rr_values": rr_values,

        "equity_curve": equity_chart_values,
        "drawdown_curve": drawdown_chart_values,

        "missing_rr_count": int(
            missing_rr_count
        ),

        "missing_close_time_count": int(
            missing_close_time_count
        ),
    }


    return render_template(
    "analytics.html",
    analytics_data=analytics_data,
    period=period,
    date_range_label=date_range_label,
)
