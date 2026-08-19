from flask import render_template, request, flash, redirect, url_for
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta
import calendar


@app.route('/analytics', methods=['GET', 'POST'])
@login_required
def analytics():
    period = request.args.get('period', 'monthly') 
    now = datetime.now()
    start_date = None
    end_date = None

    if period == 'monthly':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    elif period == 'last_month':
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = first_of_this_month - timedelta(seconds=1)
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'yearly':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    # 'all' → no filter

    filter_clause = ""
    filter_params = []
    if period != 'all':
        if start_date and end_date:
            filter_clause = "AND open_time BETWEEN ? AND ?"
            filter_params = [start_date.strftime('%Y-%m-%d %H:%M:%S'), end_date.strftime('%Y-%m-%d %H:%M:%S')]
        elif start_date:
            filter_clause = "AND open_time >= ?"
            filter_params = [start_date.strftime('%Y-%m-%d %H:%M:%S')]

    conn = get_db()

    # === TOTAL TRADES ===
    total_trades = conn.execute(f"SELECT COUNT(*) FROM trades WHERE parent_id IS NULL {filter_clause}", filter_params).fetchone()[0]

        # === CLOSED TRADES SUMMARY (NEVER SHOWS None AGAIN!) ===
    closed_raw = conn.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN RR = 0 THEN 1 ELSE 0 END) as be,
            SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END) as losses,
            SUM(RR) as sum_rr,
            AVG(RR) as avg_rr
        FROM trades 
        WHERE parent_id IS NULL AND status = 'CLOSED' AND RR IS NOT NULL {filter_clause}
    """, filter_params).fetchone()

    # Force ALL None → 0
    closed = {
        'total': closed_raw['total'] if closed_raw else 0,
        'wins': closed_raw['wins'] or 0 if closed_raw else 0,
        'be': closed_raw['be'] or 0 if closed_raw else 0,
        'losses': closed_raw['losses'] or 0 if closed_raw else 0,
        'sum_rr': closed_raw['sum_rr'] or 0 if closed_raw else 0,
        'avg_rr': closed_raw['avg_rr'] or 0 if closed_raw else 0,
    }

    closed_count = closed['total']
    win_count = closed['wins']
    loss_count = closed['losses']
    breakeven_count = closed['be']

    win_rate = round(win_count / closed_count * 100, 1) if closed_count > 0 else 0.0
    total_rr = round(closed['sum_rr'], 2)
    average_rr = round(closed['avg_rr'], 2)

        # === MEDIAN RR (100% Safe - No rowid!) ===
    median_query = f"""
        WITH ordered AS (
            SELECT RR FROM trades 
            WHERE parent_id IS NULL AND status = 'CLOSED' AND RR IS NOT NULL {filter_clause}
            ORDER BY RR
        ),
        ranked AS (
            SELECT RR,
                   ROW_NUMBER() OVER (ORDER BY RR) AS rn,
                   COUNT(*) OVER () AS cnt
            FROM ordered
        )
        SELECT AVG(RR) AS median_rr
        FROM ranked
        WHERE rn IN (FLOOR((cnt + 1)/2.0), CEIL((cnt + 1)/2.0))
    """
    median_row = conn.execute(median_query, filter_params).fetchone()
    median_rr = f"{median_row['median_rr']:.2f}" if median_row and median_row['median_rr'] else "N/A"

    # === HIGHEST RR ===
    highest_rr_row = conn.execute(f"""
        SELECT MAX(RR) FROM trades 
        WHERE parent_id IS NULL AND status = 'CLOSED' AND RR > 0 {filter_clause}
    """, filter_params).fetchone()
    highest_rr = f"{highest_rr_row[0]:.2f}" if highest_rr_row and highest_rr_row[0] else "N/A"

    # === MOST USED SYMBOL ===
    ticker = conn.execute(f"""
        SELECT symbol FROM trades 
        WHERE parent_id IS NULL AND symbol IS NOT NULL {filter_clause}
        GROUP BY symbol ORDER BY COUNT() DESC LIMIT 1
    """, filter_params).fetchone()
    most_used_ticker = ticker[0] if ticker else "N/A"

    # === LONG/SHORT ===
    ls = dict(conn.execute(f"""
        SELECT sort, COUNT(*) FROM trades 
        WHERE parent_id IS NULL AND sort IN ('LONG', 'SHORT') {filter_clause}
        GROUP BY sort
    """, filter_params).fetchall())
    long_count = ls.get('LONG', 0)
    short_count = ls.get('SHORT', 0)
    total_ls = long_count + short_count
    long_ratio = round(long_count / total_ls * 100, 1) if total_ls > 0 else 0
    short_ratio = round(short_count / total_ls * 100, 1) if total_ls > 0 else 0

    # === TYPE STATS ===
    types = ['HTF', 'MTF', 'LTF']
    trades_per_type = dict(conn.execute(f"""
        SELECT type, COUNT(*) FROM trades WHERE parent_id IS NULL {filter_clause} GROUP BY type
    """, filter_params).fetchall())
    trades_per_type_complete = {t: trades_per_type.get(t, 0) for t in types}

    type_stats = {}
    for t in types:
        row = conn.execute(f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END) as wins,
                SUM(RR) as rr
            FROM trades 
            WHERE parent_id IS NULL AND type = ? AND status = 'CLOSED' AND RR IS NOT NULL {filter_clause}
        """, [t] + filter_params).fetchone() or {'total':0, 'wins':0, 'rr':0}
        total = row['total']
        type_stats[t] = {
            'closed_count': total,
            'win_count': row['wins'],
            'win_rate': round(row['wins']/total*100, 1) if total > 0 else 0,
            'total_rr': round(row['rr'] or 0, 2)
        }

    long_short_per_type = {t: {'long_count': 0, 'short_count': 0} for t in types}
    for row in conn.execute(f"""
        SELECT type, sort, COUNT(*) FROM trades 
        WHERE parent_id IS NULL AND sort IN ('LONG','SHORT') {filter_clause}
        GROUP BY type, sort
    """, filter_params):
        if row['type'] in types:
            long_short_per_type[row['type']][f"{row['sort'].lower()}_count"] = row[2]

    total_rr_per_type = {t: type_stats[t]['total_rr'] for t in types}

    # === AVG DURATION ===
    duration = conn.execute(f"""
        SELECT AVG(julianday(close_time) - julianday(open_time)) * 86400 
        FROM trades WHERE parent_id IS NULL AND status = 'CLOSED' AND close_time IS NOT NULL {filter_clause}
    """, filter_params).fetchone()[0] or 0
    avg_trade_duration_days = round(duration / 86400, 1)

    # === RR CHART ===
    rr_labels = []
    rr_values = []

    if period == 'monthly':
        year, month = now.year, now.month
        days = calendar.monthrange(year, month)[1]
        rr_labels = [f"{year}-{month:02d}-{d:02d}" for d in range(1, days+1)]
        daily = dict(conn.execute("""
            SELECT DATE(close_time), SUM(RR) FROM trades 
            WHERE parent_id IS NULL AND status='CLOSED' AND strftime('%Y-%m', close_time)=?
            GROUP BY DATE(close_time)
        """, [f"{year}-{month:02d}"]))
        rr_values = [round(daily.get(d, 0) or 0, 2) for d in rr_labels]

    elif period == 'yearly':
        rr_labels = [calendar.month_abbr[i] for i in range(1,13)]
        monthly = dict(conn.execute("""
            SELECT strftime('%m', close_time), SUM(RR) FROM trades 
            WHERE parent_id IS NULL AND status='CLOSED' AND strftime('%Y', close_time)=?
            GROUP BY strftime('%m', close_time)
        """, [str(now.year)]))
        rr_values = [round(monthly.get(f"{i:02d}", 0) or 0, 2) for i in range(1,13)]

    elif period in ['last_month', 'all']:
        recent = conn.execute(f"""
            SELECT DATE(close_time), SUM(RR) FROM trades 
            WHERE parent_id IS NULL AND status='CLOSED' 
            ORDER BY close_time DESC LIMIT 30
        """).fetchall()
        for d, r in reversed(recent):
            rr_labels.append(d or "No Date")
            rr_values.append(round(r or 0, 2))

    analytics_data = {
        'total_trades': int(total_trades or 0),
        'win_count': int(win_count),
        'loss_count': int(loss_count),
        'breakeven_count': int(breakeven_count),
        'win_rate': float(win_rate),
        'total_rr': float(total_rr),
        'average_rr': float(average_rr),
        'median_rr': median_rr,
        'highest_rr': highest_rr,
        'most_used_ticker': most_used_ticker or "N/A",
        'avg_trade_duration': float(avg_trade_duration_days),
        'long_count': int(long_count),
        'short_count': int(short_count),
        'long_ratio': float(long_ratio),
        'short_ratio': float(short_ratio),
        'trades_per_type': trades_per_type_complete,
        'type_stats': type_stats,
        'long_short_per_type': long_short_per_type,
        'total_rr_per_type': total_rr_per_type,
        'rr_labels': rr_labels,
        'rr_values': rr_values,
    }

    return render_template('analytics.html', analytics_data=analytics_data, period=period)
