from flask import render_template, request
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta
import calendar
import math




VALID_PERIODS = {"monthly", "last_month", "yearly", "all"}
TRADE_TYPES = ("HTF", "MTF", "LTF")
DIRECTIONS = ("LONG", "SHORT")


def _date_range(period, now):
    """
    Return (start_date, end_date) for the selected analytics period.

    The application historically filters trades by open_time, so we preserve
    that behavior for compatibility.
    """
    if period == "monthly":
        start = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = (
            start.replace(day=28) + timedelta(days=4)
        ).replace(day=1) - timedelta(seconds=1)
        return start, end

    if period == "last_month":
        start_this_month = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = start_this_month - timedelta(seconds=1)
        start = end.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return start, end

    if period == "yearly":
        start = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        end = now.replace(
            month=12,
            day=31,
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        return start, end

    return None, None


def _build_filter(period, now):
    """
    Build a reusable WHERE fragment and parameter list.

    Parent trades only are analysed because partial closes are children of
    the parent and the parent RR is already recalculated from those children.
    """
    conditions = ["parent_id IS NULL"]
    params = []

    start_date, end_date = _date_range(period, now)

    if start_date and end_date:
        conditions.append("open_time >= ? AND open_time <= ?")
        params.extend([
            start_date.strftime("%Y-%m-%d %H:%M:%S"),
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    return " AND ".join(conditions), params


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _round(value, digits=2):
    return round(_safe_float(value), digits)


def _percentage(numerator, denominator, digits=1):
    if not denominator:
        return 0.0
    return round((numerator / denominator) * 100, digits)


def _calculate_streaks(rr_values):
    """
    Calculate maximum winning and losing streaks.

    Breakeven trades reset neither streak because they do not belong to
    either direction.
    """
    max_win_streak = 0
    max_loss_streak = 0

    current_win = 0
    current_loss = 0

    for rr in rr_values:
        rr = _safe_float(rr)

        if rr > 0:
            current_win += 1
            current_loss = 0
        elif rr < 0:
            current_loss += 1
            current_win = 0
        else:
            current_win = 0
            current_loss = 0

        max_win_streak = max(max_win_streak, current_win)
        max_loss_streak = max(max_loss_streak, current_loss)

    return max_win_streak, max_loss_streak


def _calculate_drawdown(rr_values):
    """
    Calculate drawdown from cumulative R.

    Returns:
        max_drawdown,
        max_drawdown_percent_of_peak,
        equity_curve,
        drawdown_curve
    """
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    equity_curve = []
    drawdown_curve = []

    for rr in rr_values:
        equity += _safe_float(rr)
        peak = max(peak, equity)

        drawdown = equity - peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown

        if peak > 0:
            dd_pct = abs(drawdown) / peak * 100
            max_drawdown_pct = max(max_drawdown_pct, dd_pct)

        equity_curve.append(round(equity, 4))
        drawdown_curve.append(round(drawdown, 4))

    return (
        round(max_drawdown, 2),
        round(max_drawdown_pct, 2),
        equity_curve,
        drawdown_curve,
    )



@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics():

    period = request.args.get("period", "monthly")

    if period not in VALID_PERIODS:
        period = "monthly"

    now = datetime.now()

    conn = get_db()
    where_clause, filter_params = _build_filter(period, now)

    total_trades = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {where_clause}
        """,
        filter_params,
    ).fetchone()[0] or 0

    open_trades = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {where_clause}
          AND status = 'OPEN'
        """,
        filter_params,
    ).fetchone()[0] or 0

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
        WHERE {where_clause}
          AND status = 'CLOSED'
          AND RR IS NOT NULL
        """,
        filter_params,
    ).fetchone()

    closed_count = int(closed_raw["total"] or 0)
    win_count = int(closed_raw["wins"] or 0)
    loss_count = int(closed_raw["losses"] or 0)
    breakeven_count = int(closed_raw["breakevens"] or 0)

    total_rr = _round(closed_raw["total_rr"])
    average_rr = _round(closed_raw["average_rr"])

    average_win = _round(closed_raw["average_win"])
    average_loss = _round(closed_raw["average_loss"])

    highest_rr = (
        _round(closed_raw["best_rr"])
        if closed_raw["best_rr"] is not None
        else None
    )

    lowest_rr = (
        _round(closed_raw["worst_rr"])
        if closed_raw["worst_rr"] is not None
        else None
    )

    gross_profit = _round(closed_raw["gross_profit"])
    gross_loss = _round(closed_raw["gross_loss"])

    win_rate = _percentage(win_count, closed_count)

    loss_rate = _percentage(loss_count, closed_count)

    breakeven_rate = _percentage(
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
            WHERE {where_clause}
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
        filter_params,
    ).fetchone()

    median_rr = (
        _round(median_row["median_rr"])
        if median_row and median_row["median_rr"] is not None
        else None
    )

    rr_rows = conn.execute(
        f"""
        SELECT RR
        FROM trades
        WHERE {where_clause}
          AND status = 'CLOSED'
          AND RR IS NOT NULL
        ORDER BY close_time ASC, id ASC
        """,
        filter_params,
    ).fetchall()

    rr_sequence = [
        _safe_float(row["RR"])
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

    max_win_streak, max_loss_streak = _calculate_streaks(
        rr_sequence
    )

    (
        max_drawdown,
        max_drawdown_pct,
        equity_curve,
        drawdown_curve,
    ) = _calculate_drawdown(rr_sequence)


    ticker_row = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS trade_count
        FROM trades
        WHERE {where_clause}
          AND symbol IS NOT NULL
          AND TRIM(symbol) != ''
        GROUP BY symbol
        ORDER BY trade_count DESC, symbol ASC
        LIMIT 1
        """,
        filter_params,
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
        WHERE {where_clause}
        AND sort IN ('LONG', 'SHORT')
        GROUP BY sort
        """,
        filter_params,
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
        wins = int(row["wins"] or 0)

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
                "win_rate": _percentage(wins, closed_count),
                "total_rr": _round(row["total_rr"]),
            }


    long_count = direction_stats["LONG"]["count"]
    short_count = direction_stats["SHORT"]["count"]

    total_direction_trades = long_count + short_count

    long_ratio = _percentage(
        long_count,
        total_direction_trades,
    )

    short_ratio = _percentage(
        short_count,
        total_direction_trades,
    )


    trades_per_type_rows = conn.execute(
        f"""
        SELECT
            type,
            COUNT(*) AS total
        FROM trades
        WHERE {where_clause}
        GROUP BY type
        """,
        filter_params,
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

            WHERE {where_clause}
            AND type = ?
            AND status = 'CLOSED'
            AND RR IS NOT NULL
            """,
            filter_params + [trade_type],
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
            "win_rate": _percentage(wins, total),
            "total_rr": _round(row["total_rr"]),
            "average_rr": _round(row["average_rr"]),
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
        WHERE {where_clause}
          AND sort IN ('LONG', 'SHORT')
        GROUP BY type, sort
        """,
        filter_params,
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

        WHERE {where_clause}
          AND status = 'CLOSED'
          AND open_time IS NOT NULL
          AND close_time IS NOT NULL
        """,
        filter_params,
    ).fetchone()

    avg_duration_seconds = _safe_float(
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

        WHERE {where_clause}
          AND status = 'CLOSED'
          AND RR IS NOT NULL
          AND close_time IS NOT NULL

        GROUP BY DATE(close_time)
        ORDER BY trade_date ASC
        """,
        filter_params,
    ).fetchall()

    daily_performance = []

    for row in daily_rows:
        daily_performance.append({
            "date": row["trade_date"],
            "rr": _round(row["total_rr"]),
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

        WHERE {where_clause}
        AND status = 'CLOSED'
        AND RR IS NOT NULL
        AND symbol IS NOT NULL
        AND TRIM(symbol) != ''

        GROUP BY symbol

        ORDER BY total_rr DESC
        """,
        filter_params,
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
            "win_rate": _percentage(wins, count),
            "total_rr": _round(row["total_rr"]),
            "average_rr": _round(row["average_rr"]),
        })


    rr_labels = []
    rr_values = []

    if period == "monthly":

        year = now.year
        month = now.month

        days = calendar.monthrange(year, month)[1]

        rr_labels = [
            f"{year}-{month:02d}-{day:02d}"
            for day in range(1, days + 1)
        ]

        daily_map = {
            row["trade_date"]: _round(row["total_rr"])
            for row in daily_rows
        }

        rr_values = [
            daily_map.get(label, 0.0)
            for label in rr_labels
        ]

    elif period == "yearly":

        rr_labels = [
            calendar.month_abbr[i]
            for i in range(1, 13)
        ]

        monthly_rows = conn.execute(
            f"""
            SELECT
                strftime('%m', close_time) AS month,
                SUM(RR) AS total_rr

            FROM trades

            WHERE {where_clause}
              AND status = 'CLOSED'
              AND RR IS NOT NULL
              AND close_time IS NOT NULL

            GROUP BY strftime('%m', close_time)
            ORDER BY month
            """,
            filter_params,
        ).fetchall()

        monthly_map = {
            row["month"]: _round(row["total_rr"])
            for row in monthly_rows
        }

        rr_values = [
            monthly_map.get(f"{month:02d}", 0.0)
            for month in range(1, 13)
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
        WHERE {where_clause}
          AND status = 'CLOSED'
          AND RR IS NULL
        """,
        filter_params,
    ).fetchone()[0] or 0

    missing_close_time_count = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM trades
        WHERE {where_clause}
          AND status = 'CLOSED'
          AND close_time IS NULL
        """,
        filter_params,
    ).fetchone()[0] or 0


    analytics_data = {

        "total_trades": int(total_trades),
        "closed_count": int(closed_count),
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
    )
