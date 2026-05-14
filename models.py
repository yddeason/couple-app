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


def seed_data():
    conn = get_db()

    # 每日一问题目（30条）
    count = conn.execute('SELECT COUNT(*) FROM daily_questions').fetchone()[0]
    if count == 0:
        daily_qs = [
            '今天让你最开心的一件事是什么？',
            '今天有没有哪个瞬间特别想对方？',
            '用三个词形容今天的心情吧～',
            '今天吃了什么好吃的？拍照了没？',
            '今天最想跟对方说的一句话是？',
            '如果今天是你们约会，最想去哪里？',
            '今天有没有遇到什么烦心事？',
            '对方做的哪件事让你觉得被爱着？',
            '今天听了什么歌？分享一句歌词吧',
            '今天第一眼看到手机时在想什么？',
            '用一个表情总结今天～',
            '今天有没有什么新的发现或感悟？',
            '对方不在身边时，什么让你想起TA？',
            '今天做了什么事觉得特别有成就感？',
            '最期待下次见面做什么？',
            '今天有没有偷偷翻看你们的聊天记录？',
            '如果现在给对方一个拥抱，想说啥？',
            '今天最想感谢对方的一件事？',
            '你今天穿什么颜色的衣服？',
            '今天的天气和你的心情像不像？',
            '有没有哪个地方让你想起第一次约会？',
            '今天笑了多少次？最因为什么笑？',
            '今天最大的遗憾是什么？',
            '对方身上你最欣赏的一点是？',
            '今天有没有做梦？梦到什么了？',
            '用一个词形容你们的关系～',
            '今天有没有学到一个新东西？',
            '最想跟对方一起完成的一件事？',
            '今天对方有没有哪句话让你心里暖暖的？',
            '闭上眼睛，第一个想到的画面是什么？',
        ]
        for i, q in enumerate(daily_qs):
            conn.execute(
                'INSERT OR IGNORE INTO daily_questions (date, question) VALUES (?, ?)',
                (f'2026-05-{i+1:02d}', q)
            )

    # 默契大考验题目
    count = conn.execute('SELECT COUNT(*) FROM quiz_questions').fetchone()[0]
    if count == 0:
        quiz_qs = [
            ('第一次约会的地点是哪里？', '回忆'),
            ('对方最喜欢吃什么？', '喜好'),
            ('对方生气了，你第一反应是？', '相处'),
            ('在一起最难忘的一天是？', '回忆'),
            ('对方最讨厌什么？', '喜好'),
            ('谁先表的白？', '回忆'),
            ('以后最想一起去的地方？', '未来'),
            ('对方最常说的口头禅是？', '了解'),
            ('吵架后谁先低头？', '相处'),
            ('对方最好的朋友叫什么？', '了解'),
            ('如果可以选一种超能力给对方，会选什么？', '未来'),
            ('对方最爱看的电影/剧是什么？', '喜好'),
            ('描述对方最可爱的一个瞬间', '了解'),
            ('理想的婚礼是什么样的？', '未来'),
            ('对方喝醉后最可能做什么？', '了解'),
            ('最想跟对方一起养的宠物是？', '未来'),
            ('对方什么时候最性感/最帅？', '了解'),
            ('如果能回到过去，想改变你们的哪个瞬间？', '回忆'),
            ('对方最擅长的技能是什么？', '了解'),
            ('你们的专属暗号或梗是什么？', '回忆'),
        ]
        for q, cat in quiz_qs:
            conn.execute(
                'INSERT OR IGNORE INTO quiz_questions (question, category) VALUES (?, ?)',
                (q, cat)
            )

    conn.commit()
    conn.close()
