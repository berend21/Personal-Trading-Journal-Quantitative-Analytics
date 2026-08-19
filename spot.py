from flask import render_template, request, flash, redirect, url_for, jsonify
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta




@app.route('/spot')
@login_required
def spot():
    date_filter = request.args.get('date_filter', 'last30')
    search_query = request.args.get('search', '').strip()
    
    page = request.args.get('page', 1, type=int)
    per_page = 30
    offset = (page - 1) * per_page

    conn = get_db()
    params = []
    now = datetime.now()

    conditions = ["parent_id IS NULL"]
    
    # Date filters (same as index)
    if date_filter == 'today':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        conditions.append("open_time >= ? AND open_time <= ?")
        params.extend([start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')])
        
    elif date_filter == 'week':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        conditions.append("open_time >= ? AND open_time <= ?")
        params.extend([start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')])
        
    elif date_filter == 'month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        conditions.append("open_time >= ? AND open_time <= ?")
        params.extend([start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')])
        
    elif date_filter == 'year':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        conditions.append("open_time >= ? AND open_time <= ?")
        params.extend([start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')])

    elif date_filter == 'last30':
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        conditions.append("open_time >= ?")
        params.append(start.strftime('%Y-%m-%d %H:%M:%S'))    

    # Search
    if search_query:
        search_param = f"%{search_query}%"
        search_conditions = [
            "symbol LIKE ?", "status LIKE ?",
            "CAST(open_price AS TEXT) LIKE ?", "CAST(close_price AS TEXT) LIKE ?",
            "reason LIKE ?", "feedback LIKE ?"
        ]
        conditions.append(f"({' OR '.join(search_conditions)})")
        params.extend([search_param] * len(search_conditions))

    where_clause = " AND ".join(conditions)

    parent_query = f"SELECT * FROM spot_trades WHERE {where_clause} ORDER BY id DESC"
    parents = conn.execute(parent_query, params).fetchall()[:500]

    # Fetch partials for all parents in ONE query
    parent_ids = [p['id'] for p in parents]
    partials_by_parent = {}

    if parent_ids:
        placeholders = ','.join(['?'] * len(parent_ids))
        partials_query = "SELECT *, parent_id FROM spot_trades WHERE parent_id IN (" + placeholders + ")"
        partial_rows = conn.execute(partials_query, parent_ids).fetchall()
        
        for row in partial_rows:
            pid = row['parent_id']
            if pid not in partials_by_parent:
                partials_by_parent[pid] = []
            partials_by_parent[pid].append(dict(row))

    # 🚀 SPOT % GAIN CALCULATION (NEW)
    processed_parents = []
    for parent_row in parents:
        parent = dict(parent_row)
        partials = partials_by_parent.get(parent['id'], [])
        
        # SPOT % GAIN: ((close_price - open_price) / open_price) * 100
        if partials:
            # Weighted average % gain for spot with partials
            total_realized_gain_pct = 0.0
            total_risk_closed = 0.0
            
            for partial in partials:
                if partial['status'] == 'CLOSED' and partial['close_price'] is not None and partial['risk'] is not None:
                    open_p = partial['open_price'] or parent['open_price']
                    if open_p and open_p != 0:
                        pct_gain = ((partial['close_price'] - open_p) / open_p) * 100
                        total_realized_gain_pct += pct_gain * partial['risk']
                        total_risk_closed += partial['risk']
            
            parent_risk = parent['risk'] if parent['risk'] is not None else 0.0
            if parent['status'] == 'CLOSED' and parent['close_price'] is not None and parent_risk > 0:
                if parent['open_price'] and parent['open_price'] != 0:
                    pct_gain = ((parent['close_price'] - parent['open_price']) / parent['open_price']) * 100
                    total_realized_gain_pct += pct_gain * parent_risk
                    total_risk_closed += parent_risk
            
            if total_risk_closed > 0:
                parent['calculated_pct_gain'] = round(total_realized_gain_pct / total_risk_closed, 2)
            else:
                parent['calculated_pct_gain'] = None
        else:
            # Single trade % gain
            if parent['status'] == 'CLOSED' and parent['open_price'] and parent['close_price'] and parent['open_price'] != 0:
                parent['calculated_pct_gain'] = round(((parent['close_price'] - parent['open_price']) / parent['open_price']) * 100, 2)
            else:
                parent['calculated_pct_gain'] = None

        if parent['status'] == 'CLOSED' and partials:
            total_closed_risk = sum(p['risk'] or 0 for p in partials if p['status'] == 'CLOSED')
            parent['risk'] = total_closed_risk or parent['risk']

        processed_parents.append(parent)

    #  MONTHLY % GAIN (not RR anymore!)
    monthly_pct_gain_result = conn.execute("""
        SELECT COALESCE(AVG(CASE 
            WHEN open_price != 0 AND close_price IS NOT NULL THEN 
            ((close_price - open_price) / open_price) * 100 
            ELSE 0 END), 0) 
        FROM spot_trades 
        WHERE parent_id IS NULL AND status = 'CLOSED' 
          AND strftime('%Y-%m', close_time) = ?
    """, (datetime.now().strftime('%Y-%m'),)).fetchone()
    monthly_pct_gain = round(monthly_pct_gain_result[0], 2)

    return render_template(
        'spot.html',
        trades=processed_parents,
        partials_by_parent=partials_by_parent,
        monthly_pct_gain=monthly_pct_gain,  #  Changed from monthly_rr
        page=page,
        date_filter=date_filter,
        search=search_query or None
    )

@app.route('/add_spot', methods=['POST'])
@login_required
def add_spot():
    symbol = request.form.get('symbol', '').upper()
    open_time = request.form.get('open_time', '').replace('T', ' ').strip()
    close_time = request.form.get('close_time', '').replace('T', ' ').strip()
    status = request.form.get('status', '').upper()
    open_price = request.form.get('open_price')
    close_price = request.form.get('close_price')
    risk = request.form.get('risk')
    SL = request.form.get('SL')
    TP = request.form.get('TP')
    reason = request.form.get('reason')
    feedback = request.form.get('feedback')

    open_dt = parse_time(open_time)
    close_dt = parse_time(close_time)
    if open_dt and close_dt and close_dt < open_dt:
        flash('Close time cannot be before open time.', 'error')
        return redirect(url_for('spot'))

    open_price = float(open_price) if open_price else None
    close_price = float(close_price) if close_price else None
    risk = float(risk) if risk else None
    SL = float(SL) if SL else None
    TP = float(TP) if TP else None

    # Spot trades use % gain, not RR
    pct_gain = None
    if close_price is not None and open_price is not None and open_price != 0:
        pct_gain = round(((close_price - open_price) / open_price) * 100, 2)

    sql = '''INSERT INTO spot_trades (symbol, open_time, close_time, status, open_price, close_price, risk, SL, TP, Gain, reason, feedback, parent_id)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

    with get_db() as conn:
        conn.execute(sql, (symbol, open_time, close_time, status, open_price, close_price, risk, SL, TP, pct_gain, reason, feedback, None))
        conn.commit()

    flash('Spot trade added!', 'success')
    return redirect(url_for('spot'))
@app.route('/edit_spot/<int:user_id>', methods=['POST'])
@login_required
def edit_spot_trade(user_id):
    try:
        conn = get_db()
        current = conn.execute('SELECT * FROM spot_trades WHERE id=?', (user_id,)).fetchone()
        if current is None:
            return jsonify({'success': False, 'message': 'Spot trade not found'})

        symbol = request.form.get('symbol', '').upper() or current['symbol']
        open_time = request.form.get('open_time', current['open_time'])
        close_time = request.form.get('close_time', current['close_time'])
        status = request.form.get('status', current['status']).upper()
        open_price = request.form.get('open_price')
        close_price = request.form.get('close_price')
        risk = request.form.get('risk')
        SL = request.form.get('SL', current['SL'])
        TP = request.form.get('TP', current['TP'])

        # Convert numeric fields
        open_price = float(open_price) if open_price else current['open_price']
        close_price = float(close_price) if close_price else current['close_price']
        risk = float(risk) if risk else current['risk']
        SL = float(SL) if SL else current['SL']
        TP = float(TP) if TP else current['TP']

        # Validate time
        open_dt = parse_time(open_time)
        close_dt = parse_time(close_time)
        if open_dt and close_dt and close_dt < open_dt:
            return jsonify({'success': False, 'message': 'Close time cannot be before open time.'})

        # Calculate % gain for spot trades
        pct_gain = None
        if close_price is not None and open_price is not None and open_price != 0:
            pct_gain = round(((close_price - open_price) / open_price) * 100, 2)

        # Update spot trade
        conn.execute('''
            UPDATE spot_trades 
            SET symbol=?, open_time=?, close_time=?, status=?, open_price=?, close_price=?, 
                risk=?, SL=?, TP=?, Gain=?
            WHERE id=?
        ''', (symbol, open_time, close_time, status, open_price, close_price, risk, SL, TP, pct_gain, user_id))
        
        conn.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
@app.route('/delete_spot/<int:user_id>', methods=['POST'])
@login_required
def delete_spot_trade(user_id):
    try:
        with get_db() as conn:
            trade = conn.execute('SELECT * FROM spot_trades WHERE id=?', (user_id,)).fetchone()
            if not trade:
                flash('Spot trade not found.', 'error')
                return redirect(url_for('spot'))

            conn.execute('DELETE FROM spot_trades WHERE id=?', (user_id,))
            conn.commit()
        
        flash('Spot trade deleted successfully!', 'success')
        return redirect(url_for('spot'))
    except Exception as e:
        flash(f'Delete failed: {str(e)}', 'error')
        return redirect(url_for('spot'))

def parse_time(s):
    if not s:
        return None
    s = s.replace('T', ' ').strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
