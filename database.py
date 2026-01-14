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
    article = conn.execute('SELECT * FROM articles WHERE query = ?', (query,)).fetchone()
    conn.close()
    return article

def get_article_by_id(article_id):
    conn = get_db_connection()
    article = conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()
    conn.close()
    return article

def add_article(query, title, content_md, image_b64):
    conn = get_db_connection()
    try:
        # Check if exists to determine insert or update
        existing = conn.execute('SELECT id FROM articles WHERE query = ?', (query,)).fetchone()
        if existing:
            conn.execute('''
                UPDATE articles
                SET title = ?, content_md = ?, image_b64 = ?, created_at = ?, is_stale = 0
                WHERE query = ?
            ''', (title, content_md, image_b64, datetime.datetime.now(), query))
        else:
            conn.execute('''
                INSERT INTO articles (query, title, content_md, image_b64, created_at, is_stale)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (query, title, content_md, image_b64, datetime.datetime.now()))
        conn.commit()
    except sqlite3.IntegrityError:
        # Should be handled by the update logic above, but safety first
        pass
    finally:
        conn.close()

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
