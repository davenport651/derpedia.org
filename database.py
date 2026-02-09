import sqlite3
import datetime

DB_NAME = 'derpedia.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            content_md TEXT NOT NULL,
            image_b64 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_stale BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_article(query):
    conn = get_db_connection()
    
    # 1. Try Exact Match (Ignoring Case)
    # This solves the "Dogzilla" vs "dogzilla" issue
    article = conn.execute(
        'SELECT * FROM articles WHERE LOWER(query) = LOWER(?)', 
        (query,)
    ).fetchone()

    # 2. If not found, Try Fuzzy Match on Title
    # This solves the "DDR4" finding "DDR4 (Double Dash...)"
    if not article:
        article = conn.execute(
            'SELECT * FROM articles WHERE LOWER(title) LIKE LOWER(?)', 
            (f'%{query}%',)
        ).fetchone()

    conn.close()
    return article

def add_article(query, title, content_md, image_b64):
    conn = get_db_connection()
    try:
        # Check if exists (Ignoring Case) so we don't create duplicates
        existing = conn.execute(
            'SELECT id FROM articles WHERE LOWER(query) = LOWER(?)', 
            (query,)
        ).fetchone()

        if existing:
            # Update existing entry
            conn.execute('''
                UPDATE articles
                SET title = ?, content_md = ?, image_b64 = ?, created_at = ?, is_stale = 0
                WHERE id = ?
            ''', (title, content_md, image_b64, datetime.datetime.now(), existing['id']))
        else:
            # Insert new entry
            conn.execute('''
                INSERT INTO articles (query, title, content_md, image_b64, created_at, is_stale)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (query, title, content_md, image_b64, datetime.datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def get_article_by_id(article_id):
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    conn.close()
    return article

def mark_stale(article_id):
    conn = get_db_connection()
    conn.execute('UPDATE articles SET is_stale = 1 WHERE id = ?', (article_id,))
    conn.commit()
    conn.close()

def get_random_article():
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE is_stale = 0 ORDER BY RANDOM() LIMIT 1').fetchone()
    conn.close()
    return article

def get_recent_articles(limit=5):
    conn = get_db_connection()
    articles = conn.execute('SELECT * FROM articles WHERE is_stale = 0 ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return articles
