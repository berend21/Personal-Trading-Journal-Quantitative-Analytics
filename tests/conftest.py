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
