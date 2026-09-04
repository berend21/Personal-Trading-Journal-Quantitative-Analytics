from flask import render_template, request, redirect, url_for, flash
from extensions import app
from login import login_required
from database import get_db
import sqlite3


@app.route('/')
@login_required
def dashboard():
    return render_template(
        'dashboard.html',
        display_name=_get_display_name(),
        today=_get_today_summary(),
        month=_get_month_summary(),
        watchlist=_get_watchlist()
    )


def _get_display_name():
    db = get_db()

    row = db.execute(
        '''
        SELECT email, display_name
        FROM users
        LIMIT 1
        '''
    ).fetchone()

    if not row:
        return 'Trader'

    if row['display_name'] and row['display_name'].strip():
        return row['display_name'].strip()

    return row['email'].split('@')[0]


def _get_today_summary():
    db = get_db()

    # Closed trades today
    row = db.execute(
        '''
        SELECT
            COUNT(*) AS trade_count,
            SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN RR = 0 THEN 1 ELSE 0 END) AS breakevens,
            COALESCE(SUM(RR), 0) AS total_r,
            COALESCE(MAX(RR), 0) AS best_r,
            COALESCE(MIN(RR), 0) AS worst_r
        FROM trades
        WHERE status = 'CLOSED'
          AND RR IS NOT NULL
          AND DATE(close_time) = DATE('now', 'localtime')
        '''
    ).fetchone()

    open_trades = db.execute(
        '''
        SELECT id, symbol, sort
        FROM trades
        WHERE status = 'OPEN'
            AND parent_id IS NULL
        ORDER BY id DESC
        '''
    ).fetchall()


    return {
        'trade_count': row['trade_count'] or 0,
        'wins': row['wins'] or 0,
        'losses': row['losses'] or 0,
        'breakevens': row['breakevens'] or 0,
        'total_r': row['total_r'] or 0,
        'best_r': row['best_r'] or 0,
        'worst_r': row['worst_r'] or 0,
        'open_trades': open_trades
    }


def _get_month_summary():
    db = get_db()

    row = db.execute(
        '''
        SELECT
            COUNT(*) AS trade_count,
            SUM(CASE WHEN RR > 0 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN RR < 0 THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN RR = 0 THEN 1 ELSE 0 END) AS breakevens,
            COALESCE(SUM(RR), 0) AS total_r
        FROM trades
        WHERE status = 'CLOSED'
          AND RR IS NOT NULL
          AND DATE(close_time) >= DATE('now', 'localtime', 'start of month')
          AND DATE(close_time) < DATE('now', 'localtime', 'start of month', '+1 month')
        '''
    ).fetchone()

    return {
        'trade_count': row['trade_count'] or 0,
        'wins': row['wins'] or 0,
        'losses': row['losses'] or 0,
        'breakevens': row['breakevens'] or 0,
        'total_r': row['total_r'] or 0
    }



@app.route('/dashboard/watchlist/add', methods=['POST'])
@login_required
def add_watchlist_ticker():
    ticker = request.form.get('ticker', '').strip().upper()

    if not ticker:
        flash('Please enter a ticker.', 'error')
        return redirect(url_for('dashboard'))

    if len(ticker) > 20:
        flash('Ticker is too long.', 'error')
        return redirect(url_for('dashboard'))

    db = get_db()

    try:
        db.execute(
            '''
            INSERT INTO watchlist (ticker)
            VALUES (?)
            ''',
            (ticker,)
        )
        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()

        existing = db.execute(
            '''
            SELECT 1
            FROM watchlist
            WHERE ticker = ?
            ''',
            (ticker,)
        ).fetchone()

        if existing:
            flash(f'{ticker} is already on your watchlist.', 'error')
        else:
            flash('Could not add ticker.', 'error')

    return redirect(url_for('dashboard'))


@app.route('/dashboard/watchlist/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_watchlist_ticker(item_id):
    db = get_db()

    db.execute(
        '''
        DELETE FROM watchlist
        WHERE id = ?
        ''',
        (item_id,)
    )

    db.commit()

    return redirect(url_for('dashboard'))


def _get_watchlist():
    db = get_db()

    return db.execute(
        '''
        SELECT id, ticker
        FROM watchlist
        ORDER BY created_at ASC, id ASC
        '''
    ).fetchall()
def _get_open_trades():
    db = get_db()

    return db.execute(
        '''
        SELECT
            id,
            symbol,
            sort,
            type_setup,
            setup,
            open_time,
            open_price,
            risk,
            SL,
            TP,
            status,
            initial_risk
        FROM trades
        WHERE status = 'OPEN'
          AND parent_id IS NULL
        ORDER BY open_time DESC
        '''
    ).fetchall()

