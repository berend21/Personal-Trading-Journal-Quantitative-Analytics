from flask import render_template, request, flash, redirect, url_for, jsonify
from extensions import app
from database import get_db
from login import login_required
from datetime import datetime, timedelta
import os
import time
from werkzeug.utils import secure_filename
from PIL import Image


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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
            parent['calculated_RR'] = calculate_parent_rr_with_partials(
                parent,
                partials
            )
        else:
            parent['calculated_RR'] = parent['RR']

        parent['RR'] = parent['calculated_RR']

        if parent['initial_risk'] is not None:

            initial_risk = float(parent['initial_risk'] or 0)

            added_risk = sum(
                float(p['risk'] or 0)
                for p in partials
                if p['risk_action'] == 'OPEN'
            )
            closed_risk = sum(
                float(p['risk'] or 0)
                for p in partials
                if p['risk_action'] == 'CLOSE'
            )
            # Risk currently still open
            parent['current_risk'] = round(
                initial_risk + added_risk - closed_risk,
                8
            )
            # Risk ever committed
            parent['total_committed_risk'] = round(
                initial_risk + added_risk,
                8
            )
            # Risk shown in the table
            if parent['status'] == 'CLOSED':
                parent['display_risk'] = round(initial_risk, 8)
            else:
                parent['display_risk'] = parent['current_risk']

        else:
            current_risk = float(parent['risk'] or 0)
            parent['current_risk'] = round(current_risk, 8)
            parent['total_committed_risk'] = round(current_risk, 8)
            parent['display_risk'] = round(current_risk, 8)

        processed_parents.append(parent)

    year_month = datetime.now().strftime('%Y-%m')

    monthly_parents = conn.execute("""
        SELECT * FROM trades
        WHERE parent_id IS NULL
        AND status = 'CLOSED'
        AND strftime('%Y-%m', close_time) = ?
    """, (year_month,)).fetchall()

    monthly_rr = 0.0

    for parent in monthly_parents:
        partials = conn.execute("""
            SELECT * FROM trades
            WHERE parent_id = ?
            ORDER BY id
        """, (parent['id'],)).fetchall()

        if partials:
            parent_rr = calculate_parent_rr_with_partials(parent, partials)
        else:
            parent_rr = parent['RR']


        if parent_rr is not None:
            monthly_rr += parent_rr

    monthly_rr = round(monthly_rr, 2)

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
    initial_risk = risk
    SL = float(SL) if SL else None
    TP = float(TP) if TP else None
    
    RR = calculate_r_multiple(sort, open_price, close_price, SL)


    sql = '''INSERT INTO trades (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, initial_risk)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''

    with get_db() as conn:
        conn.execute(sql, (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, initial_risk))    
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
            parent = conn.execute(
                'SELECT * FROM trades WHERE id=?',
                (current['parent_id'],)
            ).fetchone()

            if parent and close_price is not None and parent['SL'] is not None:
                RR = calculate_r_multiple(
                    parent['sort'],
                    open_price,
                    close_price,
                    parent['SL']
                )

                if RR is None:
                    RR = current['RR']
            else:
                RR = current['RR']

        else:
            calculated_rr = calculate_r_multiple(
                sort,
                open_price,
                close_price,
                SL
            )

            RR = calculated_rr if calculated_rr is not None else current['RR']
        if current['parent_id']:
            risk_action = 'OPEN' if status == 'OPEN' else 'CLOSE'
        else:
            risk_action = current['risk_action']


        conn.execute('''UPDATE trades SET symbol=?, open_time=?, close_time=?, type=?, status=?, sort=?, open_price=?, close_price=?, risk=?, SL=?, TP=?, RR=?, reason=?, feedback=?, risk_action=? WHERE id=?''', 
                    (symbol, open_time, close_time, type, status, sort, open_price, close_price, risk, SL, TP, RR, reason, feedback, risk_action, user_id))
        
        if current['parent_id']:
            recalculate_parent(conn, current['parent_id'])

        
        conn.commit()
         
        return {'success': True}
    
    except Exception as e:
        conn.rollback()
        return {'success': False, 'message': str(e)}
    
@app.route('/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_trade(user_id):

    with get_db() as conn:
        trade = conn.execute(
            'SELECT * FROM trades WHERE id=?',
            (user_id,)
        ).fetchone()

        if not trade:
            flash('Trade not found.', 'error')
            return redirect(url_for('index'))

        parent_id = trade['parent_id']

        # DELETING A PARENT delete all children first, then parent.
        if parent_id is None:

            conn.execute(
                'DELETE FROM trades WHERE parent_id=?',
                (user_id,)
            )

            conn.execute(
                'DELETE FROM trades WHERE id=?',
                (user_id,)
            )
        # DELETING A CHILD delete only this child, then recalculate the parent.

        else:

            conn.execute(
                'DELETE FROM trades WHERE id=?',
                (user_id,)
            )
            recalculate_parent(conn, parent_id)

        conn.commit()

    flash('Trade deleted successfully!', 'success')
    return redirect(url_for('index'))


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

            RR = calculate_r_multiple(
                parent_trade['sort'],
                open_price,
                close_price,
                parent_trade['SL']
            )

            if RR is None:
                flash(
                    'Could not calculate RR. Check direction, entry price, and stop loss.',
                    'error'
                )
                return redirect(url_for('index'))

            old_parent_risk = (
                parent_trade['risk']
                if parent_trade['risk'] is not None
                else 0.0
            )

            if risk > old_parent_risk:
                flash(
                    f'Cannot close {risk}R. Parent only has '
                    f'{old_parent_risk}R remaining.',
                    'error'
                )
                return redirect(url_for('index'))

            new_parent_risk = old_parent_risk - risk

            if new_parent_risk <= 0:
                new_parent_risk = 0.0
                new_parent_status = 'CLOSED'
                parent_close_time = (
                    parent_trade['close_time']
                    or datetime.now().strftime('%Y-%m-%d %H:%M')
                )
            else:
                new_parent_status = 'OPEN'
                parent_close_time = None


        risk_action = 'OPEN' if status == 'OPEN' else 'CLOSE'
        conn.execute('''
            INSERT INTO trades (
                symbol, open_time, close_time, type, status, sort,
                open_price, close_price, risk, SL, TP, RR,
                reason, feedback, parent_id, risk_action
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            parent_id,
            risk_action
        ))
        recalculate_parent(conn, parent_id)

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

        updated_parent = conn.execute('SELECT * FROM spot_trades WHERE id=?', (parent_id,)).fetchone()
        all_partials = conn.execute('SELECT * FROM spot_trades WHERE parent_id=?', (parent_id,)).fetchall()

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
def calculate_r_multiple(sort, open_price, close_price, stop_loss):
    if None in (open_price, close_price, stop_loss):
        return None

    try:
        open_price = float(open_price)
        close_price = float(close_price)
        stop_loss = float(stop_loss)
    except (TypeError, ValueError):
        return None

    sort = (sort or "").upper()

    if sort == "SHORT":
        risk_per_unit = stop_loss - open_price
        profit_per_unit = open_price - close_price

    elif sort == "LONG":
        risk_per_unit = open_price - stop_loss
        profit_per_unit = close_price - open_price

    else:
        return None

    if risk_per_unit <= 0:
        return None

    return profit_per_unit / risk_per_unit

def calculate_parent_rr_with_partials(parent, partials):
    total_weighted_r = 0.0
    total_closed_risk = 0.0

    for partial in partials:
        if partial['risk_action'] != 'CLOSE':
            continue

        if partial['risk'] is None:
            continue

        if partial['RR'] is None:
            continue

        risk = float(partial['risk'])
        rr = float(partial['RR'])

        if risk <= 0:
            continue

        total_weighted_r += rr * risk
        total_closed_risk += risk

    if total_closed_risk <= 0:
        return 0.0

    return round(total_weighted_r / total_closed_risk, 8)



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

def recalculate_parent(conn, parent_id):
    parent = conn.execute(
        'SELECT * FROM trades WHERE id=?',
        (parent_id,)
    ).fetchone()

    if not parent:
        return None

    children = conn.execute(
        '''
        SELECT *
        FROM trades
        WHERE parent_id=?
        ORDER BY id
        ''',
        (parent_id,)
    ).fetchall()


    if not children:

        if parent['initial_risk'] is not None:

            initial_risk = float(parent['initial_risk'] or 0)

            conn.execute(
                '''
                UPDATE trades
                SET risk=?,
                    RR=?,
                    status=?,
                    close_time=?
                WHERE id=?
                ''',
                (
                    round(initial_risk, 8),
                    0.0,
                    'OPEN',
                    None,
                    parent_id
                )
            )

            return {
                'current_risk': round(initial_risk, 8),
                'total_committed_risk': round(initial_risk, 8),
                'closed_risk': 0.0,
                'added_risk': 0.0,
                'realized_r': 0.0,
                'status': 'OPEN',
                'close_time': None
            }

        # OLD TRADE
        # No initial_risk means this is an old trade.
        return {
            'current_risk': float(parent['risk'] or 0),
            'total_committed_risk': float(parent['risk'] or 0),
            'closed_risk': 0.0,
            'added_risk': 0.0,
            'realized_r': float(parent['RR'] or 0),
            'status': parent['status'],
            'close_time': parent['close_time']
        }

    # OLD TRADES
    # Keep the existing old-trade accounting untouched for now. There is no initial_risk
    if parent['initial_risk'] is None:
        return {
            'current_risk': float(parent['risk'] or 0),
            'total_committed_risk': float(parent['risk'] or 0),
            'closed_risk': 0.0,
            'added_risk': 0.0,
            'realized_r': float(parent['RR'] or 0),
            'status': parent['status'],
            'close_time': parent['close_time']
        }
    # NEW TRADES

    initial_risk = float(parent['initial_risk'] or 0)

    added_risk = 0.0
    closed_risk = 0.0
    realized_r = 0.0

    last_close_time = None

    for child in children:

        risk = float(child['risk'] or 0)

        if child['risk_action'] == 'OPEN':
            added_risk += risk

        elif child['risk_action'] == 'CLOSE':
            closed_risk += risk

            if child['RR'] is not None:
                realized_r += float(child['RR']) * risk

            if child['close_time']:
                if (
                    last_close_time is None
                    or child['close_time'] > last_close_time
                ):
                    last_close_time = child['close_time']

    total_committed_risk = initial_risk + added_risk

    current_risk = total_committed_risk - closed_risk

    if current_risk < -0.00000001:
        raise ValueError(
            f'Parent {parent_id}: closed risk '
            f'({closed_risk}) exceeds committed risk '
            f'({total_committed_risk}).'
        )

    current_risk = max(0.0, current_risk)

    if current_risk <= 0:
        status = 'CLOSED'
        close_time = last_close_time or parent['close_time']
    else:
        status = 'OPEN'
        close_time = None

    realized_r = round(realized_r, 8)

    conn.execute(
        '''
        UPDATE trades
        SET risk=?,
            RR=?,
            status=?,
            close_time=?
        WHERE id=?
        ''',
        (
            round(current_risk, 8),
            realized_r,
            status,
            close_time,
            parent_id
        )
    )

    return {
        'current_risk': round(current_risk, 8),
        'total_committed_risk': round(total_committed_risk, 8),
        'closed_risk': round(closed_risk, 8),
        'added_risk': round(added_risk, 8),
        'realized_r': realized_r,
        'status': status,
        'close_time': close_time
    }
