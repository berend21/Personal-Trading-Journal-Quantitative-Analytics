import sqlite3
import pytest


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            open_time TEXT,
            close_time TEXT,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            sort TEXT NOT NULL,
            open_price REAL,
            close_price REAL,
            risk REAL,
            SL REAL,
            TP REAL,
            RR REAL,
            reason TEXT,
            feedback TEXT,
            reason_image TEXT,
            feedback_image TEXT,
            parent_id INTEGER,
            initial_risk REAL,
            risk_action TEXT
        )
    """)

    conn.commit()

    yield conn

    conn.close()

@pytest.fixture
def flask_db(tmp_path, monkeypatch):
    db_path = tmp_path / "flask_test.db"

    monkeypatch.setattr("database.DATABASE", str(db_path))

    import app as app_module
    from database import init_db

    app = app_module.app

    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
    )

    init_db()

    yield db_path


@pytest.fixture
def client(flask_db):
    from extensions import app

    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client, flask_db):
    conn = sqlite3.connect(flask_db)
    conn.execute(
        """
        INSERT INTO users (id, email, password, display_name)
        VALUES (1, ?, ?, ?)
        """,
        (
            "test@example.com",
            "test-password",
            "Test User",
        ),
    )
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["authenticated"] = True
        session.permanent = True

    return client




@pytest.fixture
def flask_connection(flask_db):
    conn = sqlite3.connect(flask_db)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()

@pytest.fixture
def client_with_user(client, flask_db):
    conn = sqlite3.connect(flask_db)
    conn.execute(
        """
        INSERT INTO users (id, email, password, display_name)
        VALUES (1, ?, ?, ?)
        """,
        (
            "test@example.com",
            "test-password",
            "Test User",
        ),
    )
    conn.commit()
    conn.close()

    return client
