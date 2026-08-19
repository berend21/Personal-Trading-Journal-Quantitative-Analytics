import sqlite3
import json

from flask import g
from werkzeug.security import generate_password_hash
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DATABASE = os.path.join(DATA_DIR, 'data.db')
os.makedirs(DATA_DIR, exist_ok=True)
print("DATABASE USED BY FLASK:", DATABASE)
print("DATABASE EXISTS:", os.path.exists(DATABASE))



def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    migrate_gallery_table()
    
 


    cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
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
                    parent_id INTEGER)''')

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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS journal_entries(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   date DATE NOT NULL,
                   entry_type TEXT NOT NULL CHECK(entry_type IN('daily', 'weekly', 'monthly')),
                   content TEXT,
                   week_start_date DATE,
                   month_start_date DATE,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

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
        cursor.execute("INSERT INTO journal_entries SELECT * FROM journal_entries_old") 
        cursor.execute("DROP TABLE journal_entries_old")
        print("Migrated journal_entries table: Added 'monthly' to CHECK constraint.")
    conn.commit() 

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
        CREATE INDEX IF NOT EXISTS idx_trades_open_date ON trades(open_time);
        CREATE INDEX IF NOT EXISTS idx_trades_close_date ON trades(close_time);
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
    


    user_count = cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if user_count == 0:
        default_email = 'admin@admin.com'
        default_password = '12345678'
        hashed = generate_password_hash(default_password)
        cursor.execute('INSERT INTO users (email, password) VALUES (?,?)', (default_email, hashed))

    conn.commit()
     




def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, timeout=30.0, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL;")
        g.db.execute("PRAGMA synchronous=NORMAL;")
        g.db.execute("PRAGMA cache_size=-64000;")   # 64MB cache
        g.db.execute("PRAGMA foreign_keys=ON;")
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def migrate_gallery_table():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gallery'")
    if not cursor.fetchone():
        print("Gallery table does not exist yet. Skipping migration.")
        conn.close()
        return
 
    cursor.execute("SELECT id, image_path FROM gallery")
    rows = cursor.fetchall()
    updated = False
    for row in rows:
        image_path = row['image_path']
        if image_path:  # Skip if null/empty
            try:
                json.loads(image_path)  # If it's already valid JSON, skip
            except json.JSONDecodeError:
                json_paths = json.dumps([image_path])
                cursor.execute("UPDATE gallery SET image_path = ? WHERE id = ?", (json_paths, row['id']))
                updated = True
    
    conn.commit()
    conn.close()
    if updated:
        print("Gallery table migrated to support multi-images in image_path.")
    else:
        print("Gallery table already supports multi-images.")
    
