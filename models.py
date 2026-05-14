import sqlite3
import os
from datetime import date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'couple.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT NOT NULL,
            emoji TEXT DEFAULT '',
            security_question TEXT DEFAULT '',
            security_answer TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS daily_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            question TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daily_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(question_id, user_id),
            FOREIGN KEY (question_id) REFERENCES daily_questions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            category TEXT DEFAULT 'general'
        );

        CREATE TABLE IF NOT EXISTS quiz_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            UNIQUE(session_id, question_id, user_id),
            FOREIGN KEY (session_id) REFERENCES quiz_sessions(id),
            FOREIGN KEY (question_id) REFERENCES quiz_questions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    # 兼容旧数据库：补充字段
    try:
        conn.execute('ALTER TABLE users ADD COLUMN security_question TEXT DEFAULT ""')
    except:
        pass
    try:
        conn.execute('ALTER TABLE users ADD COLUMN security_answer TEXT DEFAULT ""')
    except:
        pass

    conn.commit()
    conn.close()
