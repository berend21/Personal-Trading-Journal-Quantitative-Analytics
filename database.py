import sqlite3
import json
from flask import g
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATABASE = os.path.join(DATA_DIR, 'data.db')
os.makedirs(DATA_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON")
        
        migrate_gallery_table(conn)
        cursor = conn.cursor()
 
        cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
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
                            CHECK (risk IS NULL OR risk >= 0),
                        SL REAL
                            CHECK (SL IS NULL OR SL > 0),
                        TP REAL
                            CHECK (TP IS NULL OR TP > 0),
                        RR REAL,
                        reason TEXT,
                        feedback TEXT,
                        reason_image TEXT,
                        feedback_image TEXT,
                        parent_id INTEGER,
                        initial_risk REAL
                            CHECK (initial_risk IS NULL OR initial_risk > 0),
                        risk_action TEXT
                            CHECK (
                                risk_action IS NULL
                                OR risk_action IN ('OPEN', 'CLOSE')
                            )
                        )''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_type_setups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
        ''')
       
        migrate_trades_table(conn)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_id ON trades(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_open_time ON trades(open_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sort ON trades(sort)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_open ON trades(parent_id, open_time DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_status ON trades(parent_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_close_time ON trades(close_time)")


        cursor.execute("""CREATE TABLE IF NOT EXISTS spot_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL, 
                        open_time TEXT,
                        close_time TEXT,
                        status TEXT NOT NULL,
                        open_price REAL,
                        close_price REAL,
                        risk REAL,
                        SL REAL,
                        TP REAL,

                        reason TEXT,
                        feedback TEXT,
                        reason_image TEXT,
                        feedback_image TEXT,
                        Gain REAL,
                        parent_id INTEGER)""")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spot_trades_symbol ON spot_trades(symbol);")

        


        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY CHECK (id=1),
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                display_name TEXT
            )
        ''')
        cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in cursor.fetchall()}

        if "display_name" not in user_columns:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN display_name TEXT"
            )
            print("Added 'display_name' column to users table.")

        cursor.execute('''CREATE TABLE IF NOT EXISTS journal_entries(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    entry_type TEXT NOT NULL CHECK(entry_type IN('daily', 'weekly', 'monthly')),
                    content TEXT,
                    week_start_date DATE,
                    month_start_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')



        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_watchlist_ticker "
            "ON watchlist(ticker)"
        )


        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='journal_entries'")
        row = cursor.fetchone()
        if row and "'monthly'" not in row[0]: 
            cursor.execute("ALTER TABLE journal_entries RENAME TO journal_entries_old")
            cursor.execute('''CREATE TABLE journal_entries(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE NOT NULL,
                        entry_type TEXT NOT NULL CHECK(entry_type IN('daily', 'weekly', 'monthly')),
                        content TEXT,
                        week_start_date DATE,
                        month_start_date DATE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            cursor.execute("""
                INSERT INTO journal_entries (
                    id,
                    date,
                    entry_type,
                    content,
                    week_start_date,
                    month_start_date,
                    created_at,
                    updated_at
                )
                SELECT
                    id,
                    date,
                    entry_type,
                    content,
                    week_start_date,
                    month_start_date,
                    created_at,
                    updated_at
                FROM journal_entries_old
            """)

            cursor.execute("DROP TABLE journal_entries_old")
            print("Migrated journal_entries table: Added 'monthly' to CHECK constraint.")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_date ON journal_entries(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_type ON journal_entries(entry_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_journal_week ON journal_entries(week_start_date)")

        ##rules
        ##todo
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos1 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_type TEXT NOT NULL, -- 'ticker' or 'todo'
                content TEXT NOT NULL,
                completed INTEGER DEFAULT 0
            )
        ''')
        ###notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes1 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                color TEXT DEFAULT 'yellow',
                pinned INTEGER DEFAULT 0, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_url TEXT DEFAULT NULL
            )
        ''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS gallery (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        image_path TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gallery_title ON gallery(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gallery_description ON gallery(description)")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                featured_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                type TEXT
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_title ON knowledge_articles(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_articles(category)")

        cursor.executescript("""
            CREATE INDEX IF NOT EXISTS idx_trades_closed_rr ON trades(status, RR) WHERE status = 'CLOSED' AND RR IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_trades_parent_closed ON trades(parent_id, status) WHERE parent_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_articles(type);
        """)

        conn.executescript("""
            -- Gallery
            CREATE INDEX IF NOT EXISTS idx_gallery_created ON gallery(created_at DESC);
            
            -- Knowledge
            CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge_articles(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_knowledge_type_created ON knowledge_articles(type, created_at DESC);
            
            -- Notes
            CREATE INDEX IF NOT EXISTS idx_notes_pinned_updated ON notes1(pinned DESC, updated_at DESC);
            
            -- Journal entries
            CREATE INDEX IF NOT EXISTS idx_journal_date_type ON journal_entries(date, entry_type);
            
            -- Todos
            CREATE INDEX IF NOT EXISTS idx_todos_type ON todos1(list_type);
        """)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            color TEXT DEFAULT 'yellow',
            pinned INTEGER DEFAULT 0,
            order_index INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_category ON trading_rules(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rules_pinned ON trading_rules(pinned)")
    

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
   
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=30.0)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA busy_timeout=30000")
        
        g.db.execute("PRAGMA synchronous=FULL;")
        g.db.execute("PRAGMA cache_size=-64000;")   # 64MB cache
        g.db.execute("PRAGMA foreign_keys=ON;")
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def migrate_gallery_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'gallery'
    """)

    if not cursor.fetchone():
        print("Gallery table does not exist yet. Skipping migration.")
        return

    cursor.execute("SELECT id, image_path FROM gallery")
    rows = cursor.fetchall()

    updated = False

    for row in rows:
        row_id = row["id"]
        image_path = row["image_path"]

        if not image_path:
            continue

        try:
            parsed = json.loads(image_path)

            if not (
                isinstance(parsed, list)
                and all(isinstance(item, str) for item in parsed)
            ):
                raise ValueError("Invalid gallery image list")

        except (json.JSONDecodeError, TypeError, ValueError):
            cursor.execute(
                "UPDATE gallery SET image_path = ? WHERE id = ?",
                (json.dumps([image_path]), row_id)
            )
            updated = True

    if updated:
        print("Gallery table migrated to support multi-images in image_path.")
    else:
        print("Gallery image paths already use valid JSON string lists.")

def migrate_trades_table(conn):
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
        "risk IS NULL OR risk >= 0",
        "SL IS NULL OR SL > 0",
        "TP IS NULL OR TP > 0",
        "initial_risk IS NULL OR initial_risk > 0",
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
              AND risk < 0
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
              AND initial_risk <= 0
            """
        ),
        (
            "invalid risk_action",
            """
            SELECT id
            FROM trades
            WHERE risk_action IS NOT NULL
              AND risk_action NOT IN ('OPEN', 'CLOSE')
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
    backup_path = f"{DATABASE}.{timestamp}.backup"


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
                    CHECK (risk IS NULL OR risk >= 0),

                SL REAL
                    CHECK (SL IS NULL OR SL > 0),

                TP REAL
                    CHECK (TP IS NULL OR TP > 0),

                RR REAL,

                reason TEXT,
                feedback TEXT,
                reason_image TEXT,
                feedback_image TEXT,

                parent_id INTEGER,

                initial_risk REAL
                    CHECK (initial_risk IS NULL OR initial_risk > 0),

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

