from datetime import datetime

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

        return {
            'current_risk': float(parent['risk'] or 0),
            'total_committed_risk': float(parent['risk'] or 0),
            'closed_risk': 0.0,
            'added_risk': 0.0,
            'realized_r': float(parent['RR'] or 0),
            'status': parent['status'],
            'close_time': parent['close_time']
        }


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


def parse_float(value, field_name):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if value == '':
            return None

    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{field_name} must be a valid number.')


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
