def test_trades_requires_login(client):
    response = client.get("/trades")

    assert response.status_code == 302
    assert "/login" in response.location or "/setup" in response.location


def test_trades_page_authenticated(authenticated_client):
    response = authenticated_client.get("/trades")

    assert response.status_code == 200


def test_add_trade_requires_login(client):
    response = client.post(
        "/add",
        data={
            "symbol": "AAPL",
        },
    )

    assert response.status_code == 302


def test_add_trade_requires_symbol(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Symbol is required" in response.data

def test_add_trade_creates_trade(
    authenticated_client,
    flask_connection,
):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "open_time": "2026-08-31 10:00",
            "close_time": "",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "open_price": "100",
            "close_price": "",
            "risk": "1",
            "SL": "95",
            "TP": "110",
            "reason": "Test trade",
            "feedback": "",
        },
    )

    assert response.status_code == 302

    trade = flask_connection.execute(
        "SELECT * FROM trades WHERE symbol = ?",
        ("AAPL",),
    ).fetchone()

    assert trade is not None
    assert trade["symbol"] == "AAPL"
    assert trade["status"] == "OPEN"
    assert trade["sort"] == "LONG"
    assert trade["type"] == "HTF"
    assert trade["open_price"] == 100
    assert trade["risk"] == 1
    assert trade["SL"] == 95
    assert trade["TP"] == 110

def test_add_trade_rejects_invalid_type(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "Market",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid trade type" in response.data


def test_add_trade_rejects_invalid_status(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "INVALID",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid trade status" in response.data


def test_add_trade_rejects_invalid_direction(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "SIDEWAYS",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid trade direction" in response.data

def test_add_trade_rejects_missing_risk(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Risk is required" in response.data


def test_add_trade_rejects_zero_risk(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "0",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Risk must be greater than 0" in response.data


def test_add_trade_rejects_negative_risk(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "-1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Risk must be greater than 0" in response.data


def test_add_trade_rejects_invalid_numeric_value(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "not-a-number",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid numeric value" in response.data


def test_add_trade_rejects_long_sl_above_open(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "105",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SL must be below the open price" in response.data


def test_add_trade_rejects_short_sl_below_open(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "SHORT",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "90",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SL must be above the open price" in response.data


def test_add_trade_rejects_long_tp_below_open(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "90",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"TP must be above the open price" in response.data


def test_add_trade_rejects_short_tp_above_open(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "SHORT",
            "risk": "1",
            "open_price": "100",
            "SL": "110",
            "TP": "105",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"TP must be below the open price" in response.data


def test_add_trade_rejects_long_sl_above_tp(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "108",
            "TP": "105",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SL must be below TP" in response.data


def test_add_trade_rejects_short_sl_below_tp(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "SHORT",
            "risk": "1",
            "open_price": "100",
            "SL": "92",
            "TP": "95",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"SL must be above TP" in response.data


def test_closed_trade_requires_close_price(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "CLOSED",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
            "close_time": "2026-08-31 11:00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"CLOSED trade must have a close price" in response.data


def test_closed_trade_requires_close_time(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "CLOSED",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "close_price": "108",
            "SL": "95",
            "TP": "110",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"CLOSED trade must have a close time" in response.data


def test_open_trade_clears_close_values(
    authenticated_client,
    flask_connection,
):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "close_price": "108",
            "close_time": "2026-08-31 11:00",
            "SL": "95",
            "TP": "110",
        },
    )

    assert response.status_code == 302

    trade = flask_connection.execute(
        "SELECT * FROM trades WHERE symbol = ?",
        ("AAPL",),
    ).fetchone()

    assert trade is not None
    assert trade["status"] == "OPEN"
    assert trade["close_price"] is None
    assert trade["close_time"] is None


def test_closed_trade_is_saved_correctly(
    authenticated_client,
    flask_connection,
):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "CLOSED",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "close_price": "108",
            "close_time": "2026-08-31 11:00",
            "SL": "95",
            "TP": "110",
        },
    )

    assert response.status_code == 302

    trade = flask_connection.execute(
        "SELECT * FROM trades WHERE symbol = ?",
        ("AAPL",),
    ).fetchone()

    assert trade is not None
    assert trade["status"] == "CLOSED"
    assert trade["open_price"] == 100
    assert trade["close_price"] == 108
    assert trade["close_time"] == "2026-08-31 11:00"
    assert trade["risk"] == 1
    assert trade["RR"] is not None

def test_add_trade_rejects_invalid_open_time(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "OPEN",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "SL": "95",
            "TP": "110",
            "open_time": "not-a-date",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid open time" in response.data


def test_add_trade_rejects_invalid_close_time(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "CLOSED",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "close_price": "108",
            "SL": "95",
            "TP": "110",
            "open_time": "2026-08-31 10:00",
            "close_time": "not-a-date",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid close time" in response.data


def test_add_trade_rejects_close_before_open(authenticated_client):
    response = authenticated_client.post(
        "/add",
        data={
            "symbol": "AAPL",
            "type": "HTF",
            "status": "CLOSED",
            "sort": "LONG",
            "risk": "1",
            "open_price": "100",
            "close_price": "108",
            "SL": "95",
            "TP": "110",
            "open_time": "2026-08-31 12:00",
            "close_time": "2026-08-31 11:00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Close time cannot be before open time" in response.data

def test_edit_trade_requires_login(client):
    response = client.post(
        "/edit/1",
        data={
            "symbol": "AAPL",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.location


def test_edit_trade_not_found(authenticated_client):
    response = authenticated_client.post(
        "/edit/9999",
        data={
            "symbol": "AAPL",
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is False
    assert data["message"] == "Trade not found"


def test_edit_trade_updates_trade(
    authenticated_client,
    flask_connection,
):
    flask_connection.execute(
        """
        INSERT INTO trades (
            symbol,
            open_time,
            type,
            status,
            sort,
            open_price,
            risk,
            SL,
            TP,
            initial_risk
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "AAPL",
            "2026-08-31 10:00",
            "HTF",
            "OPEN",
            "LONG",
            100,
            1,
            95,
            110,
            1,
        ),
    )
    flask_connection.commit()

    response = authenticated_client.post(
        "/edit/1",
        data={
            "symbol": "MSFT",
            "open_time": "2026-08-31 11:00",
            "close_time": "",
            "type": "MTF",
            "status": "OPEN",
            "sort": "SHORT",
            "open_price": "200",
            "close_price": "",
            "risk": "2",
            "SL": "210",
            "TP": "180",
            "reason": "Updated reason",
            "feedback": "Updated feedback",
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is True

    trade = flask_connection.execute(
        "SELECT * FROM trades WHERE id = ?",
        (1,),
    ).fetchone()

    assert trade is not None
    assert trade["symbol"] == "MSFT"
    assert trade["type"] == "MTF"
    assert trade["status"] == "OPEN"
    assert trade["sort"] == "SHORT"
    assert trade["open_price"] == 200
    assert trade["risk"] == 2
    assert trade["SL"] == 210
    assert trade["TP"] == 180
    assert trade["reason"] == "Updated reason"
    assert trade["feedback"] == "Updated feedback"


def test_edit_trade_rejects_invalid_status(
    authenticated_client,
    flask_connection,
):
    flask_connection.execute(
        """
        INSERT INTO trades (
            symbol,
            type,
            status,
            sort,
            risk,
            initial_risk
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "AAPL",
            "HTF",
            "OPEN",
            "LONG",
            1,
            1,
        ),
    )
    flask_connection.commit()

    response = authenticated_client.post(
        "/edit/1",
        data={
            "status": "INVALID",
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is False
    assert data["message"] == "Invalid trade status."


def test_edit_trade_rejects_invalid_direction(
    authenticated_client,
    flask_connection,
):
    flask_connection.execute(
        """
        INSERT INTO trades (
            symbol,
            type,
            status,
            sort,
            risk,
            initial_risk
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "AAPL",
            "HTF",
            "OPEN",
            "LONG",
            1,
            1,
        ),
    )
    flask_connection.commit()

    response = authenticated_client.post(
        "/edit/1",
        data={
            "sort": "INVALID",
        },
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["success"] is False
    assert data["message"] == "Invalid trade direction."
