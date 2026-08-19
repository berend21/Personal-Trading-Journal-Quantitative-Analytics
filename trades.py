from flask import render_template, request, flash, redirect, url_for, jsonify, send_file
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta
import os
import time
from werkzeug.utils import secure_filename
import pandas as pd
import io
from PIL import Image

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'webm', 'ogg'}

@app.route('/')
@login_required
def index():
    date_filter = request.args.get('date_filter', 'last30')
    search_query = request.args.get('search', '').strip()

    page = request.args.get('page', 1, type=int)
    per_page = 30
    offset = (page - 1) * per_page

    conn = get_db()
    params = []
    now = datetime.now()

    conditions = ["parent_id IS NULL"]
    
    # Date filters
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

    if search_query:
        search_param = f"%{search_query}%"
        search_conditions = [
            "symbol LIKE ?", "status LIKE ?", "sort LIKE ?", "type LIKE ?",
            "CAST(open_price AS TEXT) LIKE ?", "CAST(close_price AS TEXT) LIKE ?",
            "reason LIKE ?", "feedback LIKE ?"
        ]
        conditions.append(f"({' OR '.join(search_conditions)})")
        params.extend([search_param] * len(search_conditions))

    where_clause = " AND ".join(conditions)

    parent_query = f"SELECT * FROM trades WHERE {where_clause} ORDER BY id DESC"
    parents = conn.execute(parent_query, params).fetchall()[:500]

    parent_ids = [p['id'] for p in parents]
    partials_by_parent = {}

    if parent_ids:
        placeholders = ','.join(['?'] * len(parent_ids))
        partials_query = "SELECT *, parent_id FROM trades WHERE parent_id IN (" + placeholders + ")"
        partial_rows = conn.execute(partials_query, parent_ids).fetchall()
        
        for row in partial_rows:
            pid = row['parent_id']
            if pid not in partials_by_parent:
                partials_by_parent[pid] = []
            partials_by_parent[pid].append(dict(row))

    processed_parents = []
    for parent_row in parents:
        parent = dict(parent_row)
        partials = partials_by_parent.get(parent['id'], [])
        
        if partials:
            parent['calculated_RR'] = calculate_parent_rr_with_partials(parent, partials)
        else:
            parent['calculated_RR'] = parent['RR']

        if parent['status'] == 'CLOSED' and partials:
            total_closed_risk = sum(p['risk'] or 0 for p in partials if p['status'] == 'CLOSED')
            parent['risk'] = total_closed_risk or parent['risk']

        processed_parents.append(parent)



    conn = get_db()   # already have conn = get_db() higher up
    year_month = datetime.now().strftime('%Y-%m')
    monthly_rr_result = conn.execute("""
        SELECT COALESCE(SUM(RR), 0) FROM trades
        WHERE parent_id IS NULL AND status = 'CLOSED'
        AND strftime('%Y-%m', close_time) = ?
    """, (year_month,)).fetchone()
    monthly_rr = monthly_rr_result[0] if monthly_rr_result else 0
    

     

    return render_template(
        'index.html',
        trades=processed_parents,
        partials_by_parent=partials_by_parent,
        monthly_rr=monthly_rr,
        page=page,
        date_filter=date_filter,
        search=search_query or None
    )
@app.route('/add', methods=['POST'])
@login_required
def add_trade():
    
    symbol = request.form.get('symbol', '').upper()
    open_time = request.form.get('open_time', '').replace('T', ' ').strip()
    close_time = request.form.get('close_time', '').replace('T', ' ').strip()
    type = request.form.get('type', '')
    status = request.form.get('status', '').upper()
    sort = request.form.get('sort', '').upper()
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
        return redirect(url_for('index'))

    open_price = float(open_price) if open_price else None
    close_price= float(close_price) if close_price else None
    risk = float(risk) if risk else None
    SL = float(SL) if SL else None
    TP = float(TP) if TP else None
    
    RR = ((close_price-open_price)/(open_price-SL)) if (close_price is not None) else None

    sql = '''INSERT INTO trades (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

    with get_db() as conn:
        conn.execute(sql, (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback))    
        conn.commit()
     
    flash('Trade added!', 'success')
    return redirect(url_for('index'))


@app.route('/edit/<int:user_id>', methods=['POST'])
@login_required
def edit_trade(user_id):
    try: 

        conn = get_db()
        current = conn.execute('SELECT * FROM trades WHERE id=?', (user_id,)).fetchone()
        if current is None:
            return {'success': False, 'message': 'Trade not found'}

        symbol = request.form.get('symbol', '').upper()
        open_time = request.form.get('open_time', '')
        close_time = request.form.get('close_time', '')
        type = request.form.get('type', '')
        status = request.form.get('status', '').upper()
        sort = request.form.get('sort', '').upper()
        open_price = request.form.get('open_price')
        close_price = request.form.get('close_price')
        risk = request.form.get('risk')
        SL = request.form.get('SL')
        TP = request.form.get('TP')
        reason = request.form.get('reason')
        feedback = request.form.get('feedback')

        symbol = symbol if symbol else current['symbol']
        open_time = open_time if open_time else current['open_time']
        close_time = close_time if close_time else current['close_time']
        type = type if type else current['type']
        status = status if status else current['status']
        sort = sort if sort else current['sort']
        reason = reason if reason else current['reason']
        feedback = feedback if feedback else current['feedback']

        open_price = float(open_price) if open_price else current['open_price']
        close_price = float(close_price) if close_price else current['close_price']
        risk = float(risk) if risk else current['risk']
        SL = float(SL) if SL else current['SL']
        TP = float(TP) if TP else current['TP']

        open_dt = parse_time(open_time)
        close_dt = parse_time(close_time)
        if open_dt and close_dt and close_dt < open_dt:
            return {'success': False, 'message': 'Close time cannot be before open time.'}

        if current['parent_id']:
            parent = conn.execute('SELECT * FROM trades WHERE id=?', (current['parent_id'],)).fetchone()
            if parent:
                old_risk = current['risk'] if current['risk'] is not None else 0
                new_risk = risk if risk is not None else 0
                risk_diff = new_risk - old_risk
                
                parent_new_risk = (parent['risk'] if parent['risk'] is not None else 0) + risk_diff
                
                if parent_new_risk <= 0 and parent['status'] != 'CLOSED':
                    from datetime import datetime
                    parent_close_time = datetime.now().strftime('%Y-%m-%d %H:%M')
                    parent_status = 'CLOSED'
                else:
                    parent_close_time = parent['close_time']
                    parent_status = parent['status']
                
                if parent_new_risk <= 0 and parent['status'] != 'CLOSED':
                    conn.execute('''
                        UPDATE trades SET risk=?, status=?, close_time=? WHERE id=?
                    ''', (max(0, parent_new_risk), parent_status, parent_close_time, parent['id']))
                else:
                    conn.execute('''
                        UPDATE trades SET risk=? WHERE id=?
                    ''', (parent_new_risk, parent['id']))

        if current['parent_id']:
            parent = conn.execute('SELECT * FROM trades WHERE id=?', (current['parent_id'],)).fetchone()
            if parent and close_price is not None and parent['SL'] is not None:
                if parent['sort'] == 'LONG':
                    RR = ((close_price - open_price) / (open_price - parent['SL']))
                elif parent['sort'] == 'SHORT':
                    RR = ((open_price - close_price) / (parent['SL'] - open_price))
                else:
                    RR = current['RR']
            else:
                RR = current['RR']
        else:
            RR = ((close_price-open_price)/(open_price-SL)) if (close_price is not None and SL is not None and open_price is not None) else current['RR']

        conn.execute('''UPDATE trades SET symbol=?, open_time=?, close_time=?, type=?, status=?, sort=?, open_price=?, close_price=?, risk=?, SL=?, TP=?, RR=?, reason=?, feedback=? WHERE id=?''', 
                    (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, user_id))
        
        if current['parent_id']:
            parent = conn.execute('SELECT * FROM trades WHERE id=?', (current['parent_id'],)).fetchone()
            if parent:
                all_partials = conn.execute('SELECT * FROM trades WHERE parent_id=?', (parent['id'],)).fetchall()
                parent_rr = calculate_parent_rr_with_partials(parent, all_partials)
                #print("Parent RR recalculated:", parent_rr)
                conn.execute(f'UPDATE trades SET RR=? WHERE id=?', (parent_rr, parent['id']))
        
        conn.commit()
         
        return {'success': True}
    
    except Exception as e:
        return {'success': False, 'message': str(e)}
    
@app.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_trade(user_id):

    with get_db() as conn:
        trade = conn.execute('SELECT * FROM trades WHERE id=?', (user_id,)).fetchone()
        if not trade:
            flash('Trade not found.', 'error')
            return redirect(url_for('index'))

        parent_id = trade['parent_id']

        conn.execute('DELETE FROM trades WHERE id=?', (user_id,))

        if parent_id:
            parent = conn.execute('SELECT * FROM trades WHERE id=?', (parent_id,)).fetchone()
            if parent:
                all_partials = conn.execute('SELECT * FROM trades WHERE parent_id=?', (parent_id,)).fetchall()
                parent_rr = calculate_parent_rr_with_partials(parent, all_partials)
                conn.execute('UPDATE trades SET RR=? WHERE id=?', (parent_rr, parent_id))

        conn.commit()
    flash('Trade deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/import', methods=['POST'])
@login_required
def import_trades():
    if 'import_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    file = request.files['import_file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))
    if not file.filename.endswith('.xlsx'):
        flash('Only .xlsx files are supported', 'error')
        return redirect(url_for('index'))
    try:
        df = pd.read_excel(file)
        required_columns = ['symbol', 'open_time', 'status', 'sort', 'open_price', 'risk']
        allowed_columns = [
            'id', 'symbol', 'open_time', 'close_time', 'type', 'status', 'sort', 'open_price', 'close_price', 'risk',
            'SL', 'TP', 'RR', 'reason', 'feedback', 'reason_image', 'feedback_image', 'parent_id'
        ]
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            flash("Missing required columns: {', '.join(missing)}", 'error')
            return redirect(url_for('index'))
        
        df = df[[col for col in allowed_columns if col in df.columns]]

        for col in allowed_columns:
            if col not in df.columns:
                df[col] = None

        def excel_date_to_str(val):
            if pd.isnull(val):
                return None
            if isinstance(val, float) or isinstance(val, int):
                try:
                    return pd.to_datetime('1899-12-30') + pd.to_timedelta(val, 'D')
                except Exception:
                    return None
            try:
                dt = pd.to_datetime(val, errors='coerce')
                if pd.isnull(dt):
                    return None
                return dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                return None

        for col in ['open_time', 'close_time']:
            if col in df.columns:
                df[col] = df[col].apply(excel_date_to_str)
        
        df = df[
            df['symbol'].notnull() & (df['symbol'].astype(str).str.strip() != '') &
            df['sort'].notnull() & (df['sort'].astype(str).str.strip() != '')
        ]

        numeric_cols = ['risk', 'SL', 'TP', 'pnl', 'RR']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: int(x) if pd.notnull(x) and float(x).is_integer() else (float(x) if pd.notnull(x) else None))

        if 'parent_id' in df.columns:
            df['parent_id'] = pd.to_numeric(df['parent_id'], errors='coerce')
        else:
            df['parent_id'] = None

        df['excel_id'] = df['id'] 

        parents_df = df[df['parent_id'].isnull()].copy()
        partials_df = df[df['parent_id'].notnull()].copy()

        parents_df = parents_df.sort_values(by='excel_id', ascending=True)
        partials_df = partials_df.sort_values(by='excel_id', ascending=True)

        conn = get_db()
        conn.execute('PRAGMA foreign_keys = ON')
        parent_id_map = {}
        parent_count = 0
        partial_count = 0
        

        for _, row in parents_df.iterrows():
            excel_id = row['excel_id']
            if pd.isnull(excel_id):
                continue
            excel_id = int(excel_id)
            cursor = conn.execute('''
                INSERT INTO trades (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, reason_image, feedback_image, parent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['symbol'], row['open_time'], row['close_time'], row['type'], row['status'], row['sort'],
                row['open_price'], row['close_price'], row['risk'], row['SL'], row['TP'], row['RR'], row['reason'], row['feedback'], row['reason_image'], row['feedback_image'], None
            ))
            db_id = cursor.lastrowid
            parent_id_map[excel_id] = db_id
            parent_count += 1

        for _, row in partials_df.iterrows():
            old_parent_id = row['parent_id']
            if pd.isnull(old_parent_id):
                continue
            old_parent_id = int(old_parent_id)
            db_parent_id = parent_id_map.get(old_parent_id)
            if db_parent_id is None:
                continue 
            conn.execute('''
                INSERT INTO trades (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, reason_image, feedback_image, parent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['symbol'], row['open_time'], row['close_time'], row['type'], row['status'], row['sort'],
                row['open_price'], row['close_price'], row['risk'], row['SL'], row['TP'],  row['RR'], row['reason'], row['feedback'], row['reason_image'], row['feedback_image'], db_parent_id
            ))
            partial_count += 1

        conn.commit()
         
        
        total_imported = parent_count + partial_count
        flash(f'Imported {total_imported} trades successfully! ({parent_count} parent trades, {partial_count} partial trades)', 'success')
    except Exception as e:
        flash(f'Import failed: {e}', 'error')
    return redirect(url_for('index'))

@app.route('/export')
@login_required
def export_trades():
    conn = get_db()
    df = pd.read_sql_query('SELECT * FROM trades ORDER BY id DESC', conn)
     

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Trades')
    output.seek(0)

    return send_file(output, download_name="trades_export.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/partial_close_inline/<int:parent_id>', methods=['POST'])
@login_required
def partial_close_inline(parent_id):
    with get_db() as conn:
        parent_trade = conn.execute('SELECT * FROM trades WHERE id=?', (parent_id,)).fetchone()
        if parent_trade is None:
            flash('Parent trade not found', 'error')
            return redirect(url_for('index'))

        risk = request.form.get('risk')
        status = request.form.get('status', '').upper()
        risk = float(risk) if risk else None

        reason = request.form.get('reason', '')
        feedback = request.form.get('feedback', '')

        if status not in ('OPEN', 'CLOSED'):
            flash('Invalid status', 'error')
            return redirect(url_for('index'))

        if risk is None or risk <= 0:
            flash('Risk must be provided and > 0', 'error')
            return redirect(url_for('index'))

        if status == 'OPEN':
            open_price = request.form.get('open_price')
            open_time = request.form.get('open_time')
            open_price = float(open_price) if open_price else None
            close_price = None
            close_time = None

            if open_price is None:
                flash('Open price is required for OPEN partial', 'error')
                return redirect(url_for('index'))

            RR = 0.0

            new_parent_risk = (parent_trade['risk'] if parent_trade['risk'] is not None else 0.0) + risk
            new_parent_status = parent_trade['status']
            parent_close_time = parent_trade['close_time']

        else:  
            close_price = request.form.get('close_price')
            close_time = request.form.get('close_time')
            close_price = float(close_price) if close_price else None
            open_price = parent_trade['open_price']
            open_time = None  

            if close_price is None:
                flash('Close price is required for CLOSED partial', 'error')
                return redirect(url_for('index'))

            if parent_trade['sort'] == 'LONG':
                if parent_trade['SL'] is not None:
                    denom = open_price - parent_trade['SL']
                    RR = ((close_price - open_price) / denom) if denom != 0 else 0.0
                else:
                    RR = 0.0
            elif parent_trade['sort'] == 'SHORT':
                if parent_trade['SL'] is not None:
                    denom = parent_trade['SL'] - open_price
                    RR = ((open_price - close_price) / denom) if denom != 0 else 0.0
                else:
                    RR = 0.0
            else:
                RR = 0.0

            old_parent_risk = parent_trade['risk'] if parent_trade['risk'] is not None else 0.0
            new_parent_risk = old_parent_risk - risk

            if new_parent_risk <= 0:
                new_parent_status = 'CLOSED'
                parent_close_time = parent_trade['close_time'] or datetime.now().strftime('%Y-%m-%d %H:%M')
            else:
                new_parent_status = parent_trade['status']
                parent_close_time = parent_trade['close_time']

        conn.execute('''
            INSERT INTO trades (
                symbol, open_time, close_time, type, status, sort,
                open_price, close_price, risk, SL, TP, RR,
                reason, feedback, parent_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            parent_trade['symbol'],
            open_time,
            close_time,
            parent_trade['type'],
            status,
            parent_trade['sort'],
            open_price,
            close_price,
            risk,
            parent_trade['SL'],
            parent_trade['TP'],
            RR,
            reason,
            feedback,
            parent_id
        ))

        if status == 'CLOSED' and new_parent_risk <= 0:
            conn.execute('''
                UPDATE trades
                SET risk = ?, status = ?, close_time = ?
                WHERE id = ?
            ''', (
                max(0.0, new_parent_risk),
                new_parent_status,
                parent_close_time,
                parent_id
            ))
        else:
            conn.execute('''
                UPDATE trades
                SET risk = ?, status = ?
                WHERE id = ?
            ''', (
                new_parent_risk,
                new_parent_status,
                parent_id
            ))

        updated_parent = conn.execute('SELECT * FROM trades WHERE id=?', (parent_id,)).fetchone()
        all_partials = conn.execute('SELECT * FROM trades WHERE parent_id=?', (parent_id,)).fetchall()

        parent_rr = calculate_parent_rr_with_partials(updated_parent, all_partials)

        conn.execute('UPDATE trades SET RR=? WHERE id=?', (parent_rr, parent_id))

        conn.commit()

    flash('Partial trade added!', 'success')
    return redirect(url_for('index'))



@app.route('/partial_close_inline_spot/<int:parent_id>', methods=['POST'])
@login_required
def partial_close_inline_spot(parent_id):
    with get_db() as conn:
        parent_trade = conn.execute('SELECT * FROM spot_trades WHERE id=?', (parent_id,)).fetchone()
        if parent_trade is None:
            flash('Parent spot trade not found', 'error')
            return redirect(url_for('spot'))

        risk = request.form.get('risk')
        status = request.form.get('status', '').upper()
        risk = float(risk) if risk else None

        reason = request.form.get('reason', '')
        feedback = request.form.get('feedback', '')

        if status not in ('OPEN', 'CLOSED'):
            flash('Invalid status', 'error')
            return redirect(url_for('spot'))

        if risk is None or risk <= 0:
            flash('Risk must be provided and > 0', 'error')
            return redirect(url_for('spot'))

        if status == 'OPEN':
            open_price = request.form.get('open_price')
            open_time = request.form.get('open_time')
            open_price = float(open_price) if open_price else None
            close_price = None
            close_time = None

            if open_price is None:
                flash('Open price is required for OPEN partial', 'error')
                return redirect(url_for('spot'))

            pct_gain = None
            new_parent_risk = (parent_trade['risk'] if parent_trade['risk'] is not None else 0.0) + risk
            new_parent_status = parent_trade['status']
            parent_close_time = parent_trade['close_time']

        else:  
            close_price = request.form.get('close_price')
            close_time = request.form.get('close_time')
            close_price = float(close_price) if close_price else None
            open_price = parent_trade['open_price']
            open_time = None

            if close_price is None:
                flash('Close price is required for CLOSED partial', 'error')
                return redirect(url_for('spot'))

            if open_price and open_price != 0:
                pct_gain = round(((close_price - open_price) / open_price) * 100, 2)
            else:
                pct_gain = 0.0

            old_parent_risk = parent_trade['risk'] if parent_trade['risk'] is not None else 0.0
            new_parent_risk = old_parent_risk - risk

            if new_parent_risk <= 0:
                new_parent_status = 'CLOSED'
                parent_close_time = parent_trade['close_time'] or datetime.now().strftime('%Y-%m-%d %H:%M')
            else:
                new_parent_status = parent_trade['status']
                parent_close_time = parent_trade['close_time']

        conn.execute('''
            INSERT INTO spot_trades (
                symbol, open_time, close_time, status,
                open_price, close_price, risk, SL, TP, Gain,
                reason, feedback, parent_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            parent_trade['symbol'],
            open_time,
            close_time,
            status,
            open_price,
            close_price,
            risk,
            parent_trade['SL'],
            parent_trade['TP'],
            pct_gain,
            reason,
            feedback,
            parent_id
        ))

        if status == 'CLOSED' and new_parent_risk <= 0:
            conn.execute('''
                UPDATE spot_trades
                SET risk = ?, status = ?, close_time = ?
                WHERE id = ?
            ''', (
                max(0.0, new_parent_risk),
                new_parent_status,
                parent_close_time,
                parent_id
            ))
        else:
            conn.execute('''
                UPDATE spot_trades
                SET risk = ?, status = ?
                WHERE id = ?
            ''', (
                new_parent_risk,
                new_parent_status,
                parent_id
            ))

        # Recalculate parent % gain (weighted average)
        updated_parent = conn.execute('SELECT * FROM spot_trades WHERE id=?', (parent_id,)).fetchone()
        all_partials = conn.execute('SELECT * FROM spot_trades WHERE parent_id=?', (parent_id,)).fetchall()

        # Calculate weighted average % gain
        total_realized_gain_pct = 0.0
        total_risk_closed = 0.0
        
        for partial in all_partials:
            if partial['status'] == 'CLOSED' and partial['close_price'] is not None and partial['risk'] is not None:
                open_p = partial['open_price'] or updated_parent['open_price']
                if open_p and open_p != 0:
                    pct_gain = ((partial['close_price'] - open_p) / open_p) * 100
                    total_realized_gain_pct += pct_gain * partial['risk']
                    total_risk_closed += partial['risk']
        
        parent_risk = updated_parent['risk'] if updated_parent['risk'] is not None else 0.0
        if updated_parent['status'] == 'CLOSED' and updated_parent['close_price'] is not None and parent_risk > 0:
            if updated_parent['open_price'] and updated_parent['open_price'] != 0:
                pct_gain = ((updated_parent['close_price'] - updated_parent['open_price']) / updated_parent['open_price']) * 100
                total_realized_gain_pct += pct_gain * parent_risk
                total_risk_closed += parent_risk
        
        if total_risk_closed > 0:
            parent_pct_gain = round(total_realized_gain_pct / total_risk_closed, 2)
        else:
            parent_pct_gain = None

        conn.execute('UPDATE spot_trades SET Gain=? WHERE id=?', (parent_pct_gain, parent_id))
        conn.commit()

    flash('Spot partial trade added!', 'success')
    return redirect(url_for('spot'))

@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_detail(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM trades WHERE id = ?', (user_id,)).fetchone()

    if user is None:
        flash('Not found', 'error')
         
        return redirect(url_for('index'))

    if request.method == 'POST':
        reason = request.form.get('reason', user['reason'])
        feedback = request.form.get('feedback', user['feedback'])

        delete_reason = request.form.get('delete_reason_image') == 'true'
        delete_feedback = request.form.get('delete_feedback_image') == 'true'
  
        reason_image = request.files.get('reason_image')
        feedback_image = request.files.get('feedback_image')
 
        reason_image_filename = user['reason_image']
        feedback_image_filename = user['feedback_image']

        if delete_reason:
            if user['reason_image']:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user['reason_image']))
                except OSError:
                    pass  
            reason_image_filename = None
  
        elif reason_image and reason_image.filename != '':
            if not allowed_file(reason_image.filename):
                flash('Invalid reason image file extension', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            if reason_image.content_type not in ['image/jpeg', 'image/png']:
                flash('Invalid reason image MIME type', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            try:
                reason_image.seek(0) 
                test_img = Image.open(reason_image)  
                reason_image.seek(0)  
            except Exception as e:
                flash('Faulty or corrupt reason image file', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            if user['reason_image']: 
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user['reason_image']))
                except OSError:
                    pass
            filename = secure_filename(reason_image.filename)
            filename = f"{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            reason_image.save(filepath)
            reason_image_filename = filename

        if delete_feedback:
            if user['feedback_image']:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user['feedback_image']))
                except OSError:
                    pass 
            feedback_image_filename = None

        elif feedback_image and feedback_image.filename != '':
            if not allowed_file(feedback_image.filename):
                flash('Invalid feedback image file extension', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            if feedback_image.content_type not in ['image/jpeg', 'image/png']:
                flash('Invalid feedback image MIME type', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            try:
                feedback_image.seek(0)  
                test_img = Image.open(feedback_image)  
                feedback_image.seek(0)  
            except Exception as e:
                flash('Faulty or corrupt feedback image file', 'error')
                return redirect(url_for('user_detail', user_id=user_id))  
            if user['feedback_image']:  
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], user['feedback_image']))
                except OSError:
                    pass
            filename = secure_filename(feedback_image.filename)
            filename = f"{int(time.time())}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            feedback_image.save(filepath) 
            feedback_image_filename = filename

        conn.execute('''UPDATE trades SET reason = ?, feedback = ?, reason_image = ?, feedback_image = ? WHERE id = ?''', 
                    (reason, feedback, reason_image_filename, feedback_image_filename, user_id))
        conn.commit()
         
        flash('Changes saved successfully!', 'success')
        return redirect(url_for('user_detail', user_id=user_id))  

     
    return render_template('user_detail.html', user=user)

def calculate_parent_rr_with_partials(parent, partials):
    total_realized_r = 0.0
    total_risk_closed = 0.0

    def r_multiple(sort, open_price, close_price, SL):
        if None in (open_price, close_price, SL):
            return 0.0
        try:
            if sort == 'SHORT':
                return (open_price - close_price) / (SL - open_price)
            elif sort == 'LONG':
                return (close_price - open_price) / (open_price - SL)
            else:
                return 0.0
        except ZeroDivisionError:
            return 0.0

    for partial in partials:
        if partial['status'] == 'CLOSED' and partial['close_price'] is not None and partial['risk'] is not None:
            r_mult = r_multiple(parent['sort'], partial['open_price'] or parent['open_price'], partial['close_price'], parent['SL'])
            total_realized_r += r_mult * partial['risk']
            total_risk_closed += partial['risk']

    parent_risk = parent['risk'] if parent['risk'] is not None else 0.0
    if parent['status'] == 'CLOSED' and parent['close_price'] is not None and parent_risk > 0:
        r_mult = r_multiple(parent['sort'], parent['open_price'], parent['close_price'], parent['SL'])
        total_realized_r += r_mult * parent_risk
        total_risk_closed += parent_risk

    if total_risk_closed == 0:
        return None

    return round(total_realized_r / total_risk_closed, 2)

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
