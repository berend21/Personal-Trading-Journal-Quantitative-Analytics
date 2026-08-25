from flask import render_template, request, flash, redirect, url_for
from database import get_db
from datetime import datetime, timedelta, date
from login import login_required
from extensions import app
import calendar


VALID_ENTRY_TYPES = {'daily', 'weekly', 'monthly'}


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def get_period_dates(journal_date):
    week_start = journal_date - timedelta(days=journal_date.weekday())
    month_start = journal_date.replace(day=1)

    return week_start, month_start


def save_journal_entry(conn, journal_date, entry_type, content):

    date_str = journal_date.isoformat()
    week_start, month_start = get_period_dates(journal_date)

    if entry_type == 'daily':
        existing = conn.execute("""
            SELECT id
            FROM journal_entries
            WHERE date = ?
              AND entry_type = 'daily'
            LIMIT 1
        """, (date_str,)).fetchone()

    elif entry_type == 'weekly':
        week_start_str = week_start.isoformat()

        existing = conn.execute("""
            SELECT id
            FROM journal_entries
            WHERE week_start_date = ?
              AND entry_type = 'weekly'
            LIMIT 1
        """, (week_start_str,)).fetchone()

    elif entry_type == 'monthly':
        month_start_str = month_start.isoformat()

        existing = conn.execute("""
            SELECT id
            FROM journal_entries
            WHERE month_start_date = ?
              AND entry_type = 'monthly'
            LIMIT 1
        """, (month_start_str,)).fetchone()

    else:
        raise ValueError(f"Invalid journal entry type: {entry_type}")

    if existing:
        conn.execute("""
            UPDATE journal_entries
            SET content = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (content, existing['id']))

        return 'updated'

    if entry_type == 'daily':
        conn.execute("""
            INSERT INTO journal_entries
                (date, entry_type, content)
            VALUES (?, ?, ?)
        """, (date_str, entry_type, content))

    elif entry_type == 'weekly':
        conn.execute("""
            INSERT INTO journal_entries
                (date, entry_type, content, week_start_date)
            VALUES (?, ?, ?, ?)
        """, (
            date_str,
            entry_type,
            content,
            week_start.isoformat()
        ))

    elif entry_type == 'monthly':
        conn.execute("""
            INSERT INTO journal_entries
                (date, entry_type, content, month_start_date)
            VALUES (?, ?, ?, ?)
        """, (
            date_str,
            entry_type,
            content,
            month_start.isoformat()
        ))

    return 'created'


def get_day_trades(conn, journal_date):

    start_datetime = f"{journal_date.isoformat()} 00:00:00"
    next_day = journal_date + timedelta(days=1)
    end_datetime = f"{next_day.isoformat()} 00:00:00"

    return conn.execute("""
        SELECT *,
               DATE(open_time) AS trade_date
        FROM trades
        WHERE parent_id IS NULL
          AND open_time >= ?
          AND open_time < ?
        ORDER BY open_time DESC
    """, (
        start_datetime,
        end_datetime
    )).fetchall()


def get_journal_entries(conn, journal_date):
    date_str = journal_date.isoformat()
    week_start, month_start = get_period_dates(journal_date)

    daily_entry = conn.execute("""
        SELECT *
        FROM journal_entries
        WHERE date = ?
          AND entry_type = 'daily'
        LIMIT 1
    """, (date_str,)).fetchone()

    weekly_entry = conn.execute("""
        SELECT *
        FROM journal_entries
        WHERE week_start_date = ?
          AND entry_type = 'weekly'
        LIMIT 1
    """, (week_start.isoformat(),)).fetchone()

    monthly_entry = conn.execute("""
        SELECT *
        FROM journal_entries
        WHERE month_start_date = ?
          AND entry_type = 'monthly'
        LIMIT 1
    """, (month_start.isoformat(),)).fetchone()

    return daily_entry, weekly_entry, monthly_entry


def render_daily_journal(date_str):
    journal_date = parse_date(date_str)

    if journal_date is None:
        flash('Invalid date format', 'error')
        return redirect(url_for('journal'))

    week_start, _ = get_period_dates(journal_date)

    conn = get_db()

    trades = get_day_trades(conn, journal_date)

    daily_entry, weekly_entry, monthly_entry = get_journal_entries(
        conn,
        journal_date
    )

    return render_template(
        'daily_journal.html',
        date=journal_date,
        date_str=date_str,
        week_start=week_start,
        trades=trades,
        daily_entry=daily_entry,
        weekly_entry=weekly_entry,
        monthly_entry=monthly_entry
    )


def get_month_trade_data(conn, year, month):
    """Return aggregated R performance for every trading day in a month."""

    start_date = date(year, month, 1)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    start_datetime = f"{start_date.isoformat()} 00:00:00"
    end_datetime = f"{next_month.isoformat()} 00:00:00"

    rows = conn.execute("""
        SELECT
            DATE(open_time) AS trade_date,
            COUNT(*) AS trade_count,
            COALESCE(SUM(RR), 0) AS total_r,
            COALESCE(SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END), 0) AS wins,
            COALESCE(SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END), 0) AS losses
        FROM trades
        WHERE parent_id IS NULL
          AND open_time >= ?
          AND open_time < ?
        GROUP BY DATE(open_time)
        ORDER BY trade_date
    """, (
        start_datetime,
        end_datetime
    )).fetchall()

    trades_data = {}

    for row in rows:
        trade_date = row['trade_date']

        trades_data[trade_date] = {
            'count': int(row['trade_count'] or 0),
            'total_r': float(row['total_r'] or 0),
            'wins': int(row['wins'] or 0),
            'losses': int(row['losses'] or 0)
        }

    return trades_data




def get_month_journal_data(conn, year, month):

    start_date = date(year, month, 1)

    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    start_date_str = start_date.isoformat()
    next_month_str = next_month.isoformat()

    rows = conn.execute("""
        SELECT
            date,
            entry_type,
            content,
            week_start_date,
            month_start_date
        FROM journal_entries
        WHERE
            (
                entry_type = 'daily'
                AND date >= ?
                AND date < ?
            )
            OR
            (
                entry_type = 'weekly'
                AND week_start_date >= ?
                AND week_start_date < ?
            )
            OR
            (
                entry_type = 'monthly'
                AND month_start_date >= ?
                AND month_start_date < ?
            )
    """, (
        start_date_str,
        next_month_str,
        start_date_str,
        next_month_str,
        start_date_str,
        next_month_str
    )).fetchall()

    journal_data = {}

    for row in rows:
        content = row['content'] or ''
        has_content = 1 if content.strip() else 0

        entry_type = row['entry_type']

        if entry_type == 'daily':
            calendar_date = row['date']

        elif entry_type == 'weekly':
            calendar_date = row['week_start_date']

        elif entry_type == 'monthly':
            calendar_date = row['month_start_date']

        else:
            continue

        if not calendar_date:
            continue

        if calendar_date not in journal_data:
            journal_data[calendar_date] = {}

        journal_data[calendar_date][entry_type] = has_content

    return journal_data


def render_journal_calendar():
    """Render the monthly journal calendar."""
    current_year = datetime.now().year
    current_month = datetime.now().month

    try:
        year = int(request.args.get('year', current_year))
        month = int(request.args.get('month', current_month))
    except (TypeError, ValueError):
        flash('Invalid calendar date', 'error')
        year = current_year
        month = current_month

    if year < 1 or year > 9999:
        flash('Invalid year', 'error')
        year = current_year

    if month < 1 or month > 12:
        flash('Invalid month', 'error')
        month = current_month

    cal = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

    month_name = calendar.month_name[month]

    weekday_names = [
        'Sun',
        'Mon',
        'Tue',
        'Wed',
        'Thu',
        'Fri',
        'Sat'
    ]


    conn = get_db()

    trades_data = get_month_trade_data(
        conn,
        year,
        month
    )

    journal_data = get_month_journal_data(
        conn,
        year,
        month
    )

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template(
        'journal.html',
        calendar_data=cal,
        weekday_names=weekday_names,
        year=year,
        month=month,
        month_name=month_name,
        trades_data=trades_data,
        journal_data=journal_data,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
        today=date.today().isoformat()
    )



@app.route('/journal', methods=['GET', 'POST'])
@app.route('/journal/<date_str>', methods=['GET', 'POST'])
@login_required
def journal(date_str=None):

    if request.method == 'POST':

        date_str = request.form.get('date', '').strip()
        entry_type = request.form.get('entry_type', '').strip().lower()
        content = request.form.get('content', '').strip()

        if entry_type not in VALID_ENTRY_TYPES:
            flash('Invalid journal entry type', 'error')
            return redirect(url_for('journal'))

        journal_date = parse_date(date_str)

        if journal_date is None:
            flash('Invalid date format', 'error')
            return redirect(url_for('journal'))

        conn = get_db()

        try:
            save_journal_entry(
                conn,
                journal_date,
                entry_type,
                content
            )

            conn.commit()

            flash(
                f'{entry_type.title()} journal saved!',
                'success'
            )

        except Exception as e:
            conn.rollback()

            print(f"Database error while saving journal entry: {e}")

            flash(
                'Error saving journal entry',
                'error'
            )

        return redirect(
            url_for(
                'journal',
                date_str=journal_date.isoformat()
            )
        )

    if date_str:
        return render_daily_journal(date_str)

    return render_journal_calendar()
