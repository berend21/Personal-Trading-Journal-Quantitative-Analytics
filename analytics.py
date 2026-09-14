from flask import render_template, request
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta

from asset_classifier import get_asset_class, ASSET_CLASSES

VALID_ATTRIBUTIONS = {"entry", "exit"}
TRADE_TYPES = ("HTF", "MTF", "LTF")
DIRECTIONS = ("LONG", "SHORT")

from analyze.statistics import (safe_float, roundit, percentage, calculate_streaks, calculate_drawdown, calculate_trade_statistics)
from analyze.distribution import calculate_r_distribution
from analyze.confidence_interval import (confidence_interval, classify_confidence_interval, classify_sample_size)
from analyze.expectancy import calculate_expectancy
from analyze.attribution import calculate_asset_class_stats
from analyze.filters import (VALID_PERIODS, date_range, build_filter, parse_custom_dates)

@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics():

    period = request.args.get("period", "monthly")

    if period not in VALID_PERIODS:
        period = "monthly"
        
    try:
        custom_start, custom_end = parse_custom_dates(
            period,
            request.args.get("start"),
            request.args.get("end"),
        )
    except ValueError:
        return "Invalid custom date range", 400

        
    now = datetime.now()
 
    conn = get_db()


    display_start, display_end = date_range(
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


    performance_where, performance_params = build_filter(
        period,
        now,
        date_field="close_time",
        custom_start=custom_start,
        custom_end=custom_end,
    )

    entry_where, entry_params = build_filter(
        period,
        now,
        date_field="open_time",
        custom_start=custom_start,
        custom_end=custom_end,
    )

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

    asset_class_stats = calculate_asset_class_stats(
        asset_class_rows
    )


    asset_class_rr_rows = conn.execute(
        f"""
        SELECT
            symbol,
            RR
        FROM trades
        WHERE {performance_where}
        AND status = 'CLOSED'
        AND RR IS NOT NULL
        """,
        performance_params,
    ).fetchall()


    asset_class_rr_sequences = {
        asset_class: []
        for asset_class in ASSET_CLASSES
    }


    for row in asset_class_rr_rows:

        symbol = (row["symbol"] or "").strip().upper()
        asset_class = get_asset_class(symbol)

        if asset_class not in asset_class_rr_sequences:
            asset_class_rr_sequences[asset_class] = []

        asset_class_rr_sequences[asset_class].append(
            safe_float(row["RR"])
        )


    for asset_class, stats in asset_class_stats.items():

        rr_sequence = asset_class_rr_sequences.get(
            asset_class,
            []
        )

        expectancy_ci = confidence_interval(
            rr_sequence
        )

        raw_expectancy = calculate_expectancy(
            rr_sequence
        )

        stats["expectancy"] = (
            roundit(raw_expectancy)
            if raw_expectancy is not None
            else 0.0
        )

        stats["expectancy_ci"] = expectancy_ci

        stats["expectancy_ci_classification"] = (
            classify_confidence_interval(
                expectancy_ci
            )
        )

        stats["sample_strength"] = classify_sample_size(
            len(rr_sequence)
        )

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
    trade_stats = calculate_trade_statistics(
        rr_sequence
    )
    

    r_distribution = calculate_r_distribution(
        rr_sequence
    )

    expectancy_ci = confidence_interval(rr_sequence)

    expectancy_ci_classification = classify_confidence_interval(
        expectancy_ci
    )

    expectancy_sample_size = len(rr_sequence)

    expectancy_sample_strength = classify_sample_size(
        expectancy_sample_size
    )

    max_win_streak, max_loss_streak = calculate_streaks(
        rr_sequence
    )

    drawdown = calculate_drawdown(rr_sequence)

    max_drawdown = drawdown["max_drawdown"]
    current_drawdown = drawdown["current_drawdown"]
    equity_curve = drawdown["equity_curve"]
    drawdown_curve = drawdown["drawdown_curve"]


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

            SUM(CASE
                    WHEN status = 'CLOSED'
                    AND RR IS NOT NULL
                    THEN 1
                    ELSE 0
                END) AS closed_count,

            SUM(CASE
                    WHEN status = 'CLOSED'
                    AND RR > 0
                    THEN 1
                    ELSE 0
                END) AS wins,

            SUM(CASE
                    WHEN status = 'CLOSED'
                    AND RR IS NOT NULL
                    THEN RR
                    ELSE 0
                END) AS total_rr

        FROM trades
        WHERE {performance_where}
        AND sort IN ('LONG', 'SHORT')
        GROUP BY sort
        """,
        performance_params,
    ).fetchall()


    direction_rr_rows = conn.execute(
        f"""
        SELECT
            sort,
            RR
        FROM trades
        WHERE {performance_where}
        AND status = 'CLOSED'
        AND RR IS NOT NULL
        AND sort IN ('LONG', 'SHORT')
        ORDER BY close_time ASC, id ASC
        """,
        performance_params,
    ).fetchall()


    direction_rr_sequences = {
        "LONG": [],
        "SHORT": [],
    }

    for row in direction_rr_rows:

        direction = row["sort"]

        if direction in direction_rr_sequences:
            direction_rr_sequences[direction].append(
                safe_float(row["RR"])
            )


    direction_stats = {
        direction: {
            "count": 0,
            "closed_count": 0,
            "wins": 0,
            "win_rate": 0.0,
            "total_rr": 0.0,
            "expectancy": 0.0,
            "expectancy_ci": None,
            "expectancy_ci_classification": "insufficient_data",
            "sample_strength": classify_sample_size(0),
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

        rr_values = direction_rr_sequences.get(
            direction,
            []
        )

        direction_expectancy_ci = confidence_interval(
            rr_values
        )

        direction_ci_classification = (
            classify_confidence_interval(
                direction_expectancy_ci
            )
        )

        direction_sample_strength = classify_sample_size(
            len(rr_values)
        )
        raw_direction_expectancy = calculate_expectancy(
            rr_values
        )

        direction_stats[direction] = {
            "count": count,
            "closed_count": closed_count,
            "wins": wins,
            "win_rate": percentage(wins, closed_count),
            "total_rr": roundit(row["total_rr"]),

            "expectancy": (
                roundit(raw_direction_expectancy)
                if raw_direction_expectancy is not None
                else 0.0
            ),

            "expectancy_ci": direction_expectancy_ci,

            "expectancy_ci_classification":
                direction_ci_classification,

            "sample_strength":
                direction_sample_strength,
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

                SUM(CASE WHEN RR > 0 THEN 1  ELSE 0 END) AS wins,

                SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END) AS losses,

                SUM(CASE WHEN RR = 0 THEN 1  ELSE 0 END) AS breakevens,

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
            "expectancy_ci": None,
            "expectancy_ci_classification": "insufficient_data",
            "sample_strength": classify_sample_size(total),
        }
        type_rr_rows = conn.execute(
            f"""
            SELECT RR
            FROM trades
            WHERE {performance_where}
            AND type = ?
            AND status = 'CLOSED'
            AND RR IS NOT NULL
            ORDER BY close_time ASC, id ASC
            """,
            performance_params + [trade_type],
        ).fetchall()

        type_rr_sequence = [
            safe_float(row["RR"])
            for row in type_rr_rows
        ]

        type_ci = confidence_interval(
            type_rr_sequence
        )

        raw_type_expectancy = calculate_expectancy(
            type_rr_sequence
        )

        type_stats[trade_type]["expectancy"] = (
            roundit(raw_type_expectancy)
            if raw_type_expectancy is not None
            else 0.0
        )

        type_stats[trade_type]["expectancy_ci"] = type_ci

        type_stats[trade_type][
            "expectancy_ci_classification"
        ] = classify_confidence_interval(
            type_ci
        )

        type_stats[trade_type]["sample_strength"] = (
            classify_sample_size(
                len(type_rr_sequence)
            )
        )

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


    positive_expectancy = trade_stats["expectancy"] > 0



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

        "closed_count": int(overview_closed_count),

        "win_count": trade_stats["win_count"],
        "loss_count": trade_stats["loss_count"],
        "breakeven_count": trade_stats["breakeven_count"],

        "win_rate": trade_stats["win_rate"],
        "loss_rate": trade_stats["loss_rate"],
        "breakeven_rate": trade_stats["breakeven_rate"],

        "total_rr": trade_stats["total_rr"],
        "average_rr": trade_stats["average_rr"],
        "median_rr": trade_stats["median_rr"],

        "expectancy": trade_stats["expectancy"],


        "expectancy_ci": expectancy_ci,
        "expectancy_ci_classification": expectancy_ci_classification,

        "expectancy_sample_size": expectancy_sample_size,
        "expectancy_sample_strength": expectancy_sample_strength,



        "highest_rr": trade_stats["highest_rr"],
        "lowest_rr": trade_stats["lowest_rr"],

        "average_win": trade_stats["average_win"],
        "average_loss": trade_stats["average_loss"],

        "gross_profit": trade_stats["gross_profit"],
        "gross_loss": trade_stats["gross_loss"],

        "profit_factor": trade_stats["profit_factor"],
        "payoff_ratio": trade_stats["payoff_ratio"],

        "rr_stddev": trade_stats["rr_stddev"],


        "max_drawdown": float(max_drawdown),
        "current_drawdown": float(current_drawdown),
        "r_distribution": r_distribution,

        "max_drawdown_duration": int(
            drawdown["max_drawdown_duration"]
        ),
        "recovery_trades": (
            int(drawdown["recovery_trades"])
            if drawdown["recovery_trades"] is not None
            else None
        ),


        "max_win_streak": int(max_win_streak),
        "max_loss_streak": int(max_loss_streak),

  

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
