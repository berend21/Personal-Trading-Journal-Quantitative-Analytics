import sqlite3
from datetime import datetime

def migrate_trades_table(conn, database):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'trades'
    """)
    row = cursor.fetchone()

    if not row:
        return

    table_sql = row[0] or ""

    cursor.execute("PRAGMA table_info(trades)")
    columns = {row[1] for row in cursor.fetchall()}

    if "type_setup" not in columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN type_setup TEXT")
        print("Added 'type_setup' column to trades table.")

    if "confidence" not in columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN confidence INTEGER")
        print("Added 'confidence' column to trades table.")

    if "setup" not in columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN setup TEXT")
        print("Added 'setup' column to trades table.")

    if "initial_risk" not in columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN initial_risk REAL")
        print("Added 'initial_risk' column to trades table.")

    if "risk_action" not in columns:
        cursor.execute("ALTER TABLE trades ADD COLUMN risk_action TEXT ")
        print("Added 'risk_action' column to trades table.")


    required_constraints = [
        "type IN ('HTF', 'MTF', 'LTF')",
        "confidence IS NULL OR confidence BETWEEN 1 AND 10",
        "status IN ('OPEN', 'CLOSED')",
        "sort IN ('LONG', 'SHORT')",
        "risk IS NULL OR (risk >= 0 AND risk <= 100)",
        "SL IS NULL OR SL > 0",
        "TP IS NULL OR TP > 0",
        "RR IS NULL OR (RR >= -1000 AND RR <= 1000)",
        "initial_risk IS NULL OR (initial_risk >= 0 AND initial_risk <= 100)",
        "risk_action IS NULL OR risk_action IN ('OPEN', 'CLOSE')",
        "open_price IS NULL OR open_price >= 0",
        "close_price IS NULL OR close_price >= 0",
    ]


    if all(constraint in table_sql for constraint in required_constraints):
        print("Trades table constraints already present.")
        return

    print("Trades table requires constraint migration.")

    checks = [
        (
            "invalid type",
            """
            SELECT id
            FROM trades
            WHERE type NOT IN ('HTF', 'MTF', 'LTF')
            """
        ),
        (
            "invalid confidence",
            """
            SELECT id
            FROM trades
            WHERE confidence IS NOT NULL
            AND confidence NOT BETWEEN 1 AND 10
            """
        ),
        (
            "invalid status",
            """
            SELECT id
            FROM trades
            WHERE status NOT IN ('OPEN', 'CLOSED')
            """
        ),
        (
            "invalid sort",
            """
            SELECT id
            FROM trades
            WHERE sort NOT IN ('LONG', 'SHORT')
            """
        ),
        (
            "invalid risk",
            """
            SELECT id
            FROM trades
            WHERE risk IS NOT NULL
            AND (risk < 0 OR risk > 100)
            """
        ),
        (
            "invalid SL",
            """
            SELECT id
            FROM trades
            WHERE SL IS NOT NULL
              AND SL <= 0
            """
        ),
        (
            "invalid TP",
            """
            SELECT id
            FROM trades
            WHERE TP IS NOT NULL
              AND TP <= 0
            """
        ),
        (
            "invalid initial_risk",
            """
            SELECT id
            FROM trades
            WHERE initial_risk IS NOT NULL
            AND (initial_risk < 0 OR initial_risk > 100)
            """
        ),
        (
            "invalid open_price",
            """
            SELECT id
            FROM trades
            WHERE open_price IS NOT NULL
              AND open_price < 0
            """
        ),
        (
            "invalid RR",
            """
            SELECT id
            FROM trades
            WHERE RR IS NOT NULL
            AND (RR < -1000 OR RR > 1000)
            """
        ),
        (
            "invalid close_price",
            """
            SELECT id
            FROM trades
            WHERE close_price IS NOT NULL
              AND close_price < 0
            """
        ),
    ]

    for description, query in checks:
        rows = cursor.execute(query).fetchall()

        if rows:
            ids = [row[0] for row in rows]

            raise RuntimeError(
                f"Trades migration aborted: {description}. "
                f"Trade IDs: {ids}"
            )

    print("Existing trades passed all constraint checks.")

  
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{database}.{timestamp}.backup"


    backup_conn = sqlite3.connect(backup_path)

    try:
        conn.backup(backup_conn)
        backup_conn.commit()
        print(f"Fresh database backup created: {backup_path}")
    finally:
        backup_conn.close()


  
    try:

        cursor.execute("DROP TABLE IF EXISTS trades_new")
        cursor.execute("""
            CREATE TABLE trades_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                open_time TEXT,
                close_time TEXT,
                type TEXT NOT NULL
                    CHECK (type IN ('HTF', 'MTF', 'LTF')),
                type_setup TEXT,
                confidence INTEGER
                    CHECK (confidence IS NULL OR confidence BETWEEN 1 AND 10),
                setup TEXT,

                status TEXT NOT NULL
                    CHECK (status IN ('OPEN', 'CLOSED')),

                sort TEXT NOT NULL
                    CHECK (sort IN ('LONG', 'SHORT')),

                open_price REAL
                    CHECK (open_price IS NULL OR open_price >= 0),

                close_price REAL
                    CHECK (close_price IS NULL OR close_price >= 0),

                risk REAL
                    CHECK (risk IS NULL OR (risk >= 0 AND risk <= 100)),

                SL REAL
                    CHECK (SL IS NULL OR SL > 0),

                TP REAL
                    CHECK (TP IS NULL OR TP > 0),

                RR REAL
                    CHECK (RR IS NULL OR (RR >= -1000 AND RR <= 1000)),

                reason TEXT,
                feedback TEXT,
                reason_image TEXT,
                feedback_image TEXT,

                parent_id INTEGER,

                initial_risk REAL
                    CHECK (initial_risk IS NULL OR (initial_risk >= 0 AND initial_risk <= 100)),

                risk_action TEXT
                    CHECK (
                        risk_action IS NULL
                        OR risk_action IN ('OPEN', 'CLOSE')
                    )
            )
        """)

        cursor.execute("""
            INSERT INTO trades_new (
                id,
                symbol,
                open_time,
                close_time,
                type,
                type_setup,
                confidence,
                setup,
                status,
                sort,
                open_price,
                close_price,
                risk,
                SL,
                TP,
                RR,
                reason,
                feedback,
                reason_image,
                feedback_image,
                parent_id,
                initial_risk,
                risk_action
            )
            SELECT
                id,
                symbol,
                open_time,
                close_time,
                type,
                type_setup,
                confidence,
                setup,
                status,
                sort,
                open_price,
                close_price,
                risk,
                SL,
                TP,
                RR,
                reason,
                feedback,
                reason_image,
                feedback_image,
                parent_id,
                initial_risk,
                risk_action
            FROM trades
        """)

        old_count = cursor.execute(
            "SELECT COUNT(*) FROM trades"
        ).fetchone()[0]

        new_count = cursor.execute(
            "SELECT COUNT(*) FROM trades_new"
        ).fetchone()[0]

        if old_count != new_count:
            raise RuntimeError(
                f"Migration aborted: row count changed "
                f"from {old_count} to {new_count}."
            )

        print(f"Verified {new_count} trades copied successfully.")
        missing_from_new = cursor.execute("""
            SELECT id FROM trades
            EXCEPT
            SELECT id FROM trades_new
        """).fetchall()

        missing_from_old = cursor.execute("""
            SELECT id FROM trades_new
            EXCEPT
            SELECT id FROM trades
        """).fetchall()

        if missing_from_new:
            ids = [row[0] for row in missing_from_new]
            raise RuntimeError(
                f"Migration aborted: IDs missing from trades_new: {ids}"
            )

        if missing_from_old:
            ids = [row[0] for row in missing_from_old]
            raise RuntimeError(
                f"Migration aborted: unexpected IDs in trades_new: {ids}"
            )

        print("Verified: all trade IDs match.")

        critical_mismatches = cursor.execute("""
            SELECT o.id
            FROM trades o
            JOIN trades_new n ON n.id = o.id
            WHERE
                o.symbol IS NOT n.symbol
                OR o.open_time IS NOT n.open_time
                OR o.close_time IS NOT n.close_time
                OR o.type IS NOT n.type
                OR o.type_setup IS NOT n.type_setup
                OR o.confidence IS NOT n.confidence
                OR o.setup IS NOT n.setup
                OR o.status IS NOT n.status
                OR o.sort IS NOT n.sort
                OR o.open_price IS NOT n.open_price
                OR o.close_price IS NOT n.close_price
                OR o.risk IS NOT n.risk
                OR o.SL IS NOT n.SL
                OR o.TP IS NOT n.TP
                OR o.RR IS NOT n.RR
                OR o.reason IS NOT n.reason
                OR o.feedback IS NOT n.feedback
                OR o.reason_image IS NOT n.reason_image
                OR o.feedback_image IS NOT n.feedback_image
                OR o.parent_id IS NOT n.parent_id
                OR o.initial_risk IS NOT n.initial_risk
                OR o.risk_action IS NOT n.risk_action
            ORDER BY o.id
        """).fetchall()

        if critical_mismatches:
            ids = [row[0] for row in critical_mismatches]
            raise RuntimeError(
                f"Migration aborted: critical field mismatch "
                f"for trade IDs: {ids}"
            )

        print("Verified: all critical trade fields match.")


        cursor.execute("DROP TABLE trades")

        cursor.execute("""
            ALTER TABLE trades_new
            RENAME TO trades
        """)
        final_count = cursor.execute(
            "SELECT COUNT(*) FROM trades"
        ).fetchone()[0]

        if final_count != old_count:
            raise RuntimeError(
                f"Migration verification failed: expected "
                f"{old_count} trades, found {final_count}."
            )

        print(f"Final verification passed: {final_count} trades.")

        integrity = cursor.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"SQLite integrity check failed: {integrity}"
            )

        print("SQLite integrity check passed.")
        print("Verified trades table constraints.")

        conn.commit()


        print("Trades table migration completed successfully.")

    except Exception:
        conn.rollback()
        raise

