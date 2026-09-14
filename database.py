import sqlite3
from flask import g
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATABASE = os.path.join(DATA_DIR, 'data.db')
os.makedirs(DATA_DIR, exist_ok=True)

from migrations.gallery_migration import migrate_gallery_table
from migrations.trade_migration import migrate_trades_table

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
                        )''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_type_setups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
        ''')
       
        migrate_trades_table(conn, DATABASE)
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
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_type TEXT NOT NULL, -- 'ticker' or 'todo'
                content TEXT NOT NULL,
                completed INTEGER DEFAULT 0
            )
        ''')
        ###notes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
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
            CREATE INDEX IF NOT EXISTS idx_gallery_created ON gallery(created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge_articles(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_knowledge_type_created ON knowledge_articles(type, created_at DESC);
       
            CREATE INDEX IF NOT EXISTS idx_notes_pinned_updated ON notes(pinned DESC, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_journal_date_type ON journal_entries(date, entry_type);
            
            CREATE INDEX IF NOT EXISTS idx_todos_type ON todos(list_type);
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
        g.db.execute("PRAGMA cache_size=-64000;")   
        g.db.execute("PRAGMA foreign_keys=ON;")
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
