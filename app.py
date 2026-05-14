from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from models import get_db
from datetime import date
import random

app = Flask(__name__)
app.secret_key = 'couple-app-secret-key-2026'


# ── 登录校验 ──

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped


# ── 路由：登录 / 退出 ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['display_name'] = user['display_name']
            session['emoji'] = user['emoji']
            return redirect(url_for('home'))
        return render_template('login.html', error='账号或密码错误')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    if count >= 2:
        db.close()
        return render_template('register.html', error='已有两个账号，无法再注册', full=True)

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        display_name = request.form.get('display_name', '').strip()
        emoji = request.form.get('emoji', '💙').strip()
        sec_q = request.form.get('security_question', '').strip()
        sec_a = request.form.get('security_answer', '').strip()

        errors = []
        if not all([username, password, display_name, sec_q, sec_a]):
            errors.append('请填写所有字段')
        if len(password) < 4:
            errors.append('密码至少 4 位')
        if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
            errors.append('用户名已被使用')

        if errors:
            db.close()
            return render_template('register.html', error='；'.join(errors))

        db.execute(
            'INSERT INTO users (username, password, display_name, emoji, security_question, security_answer) VALUES (?, ?, ?, ?, ?, ?)',
            (username, generate_password_hash(password), display_name, emoji, sec_q, generate_password_hash(sec_a))
        )
        db.commit()
        db.close()
        return render_template('login.html', success='注册成功，请登录')

    db.close()
    return render_template('register.html')


@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if not user:
            db.close()
            return render_template('forgot.html', step=1, error='用户名不存在')

        if not user['security_question']:
            db.close()
            return render_template('forgot.html', step=1, error='该账号未设置安全问题，无法找回')

        db.close()
        return render_template('forgot.html', step=2, username=username, question=user['security_question'])

    return render_template('forgot.html', step=1)


@app.route('/reset-password', methods=['POST'])
def reset_password():
    username = request.form.get('username', '').strip()
    answer = request.form.get('answer', '').strip()
    new_password = request.form.get('new_password', '')

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        db.close()
        return render_template('forgot.html', step=1, error='用户名不存在')

    if not check_password_hash(user['security_answer'], answer):
        db.close()
        return render_template('forgot.html', step=2, username=username, question=user['security_question'], error='安全问题答案错误')

    if len(new_password) < 4:
        db.close()
        return render_template('forgot.html', step=2, username=username, question=user['security_question'], error='新密码至少 4 位')

    db.execute('UPDATE users SET password = ? WHERE username = ?',
               (generate_password_hash(new_password), username))
    db.commit()
    db.close()
    return render_template('login.html', success='密码重置成功，请登录')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── 首页 ──

@app.route('/')
@login_required
def home():
    return render_template('home.html')


# ── 每日一问 ──

@app.route('/daily', methods=['GET', 'POST'])
@login_required
def daily():
    db = get_db()
    today = str(date.today())

    # 找到或创建今天的问题
    q = db.execute(
        'SELECT * FROM daily_questions WHERE date = ?', (today,)
    ).fetchone()

    if not q:
        # 循环取题：按天数取模
        count = db.execute('SELECT COUNT(*) FROM daily_questions').fetchone()[0]
        if count == 0:
            db.close()
            return '还没有题目，请先运行 init_db.py'
        idx = date.today().toordinal() % count
        q = db.execute(
            'SELECT * FROM daily_questions LIMIT 1 OFFSET ?', (idx,)
        ).fetchone()
        # 绑定到今天
        db.execute(
            'INSERT OR IGNORE INTO daily_questions (date, question) VALUES (?, ?)',
            (today, q['question'])
        )
        db.commit()
        q = db.execute(
            'SELECT * FROM daily_questions WHERE date = ?', (today,)
        ).fetchone()

    # 自己和对方的回答
    my_answer = db.execute(
        'SELECT * FROM daily_answers WHERE question_id = ? AND user_id = ?',
        (q['id'], session['user_id'])
    ).fetchone()

    partner = db.execute(
        'SELECT * FROM users WHERE id != ?', (session['user_id'],)
    ).fetchone()
    partner_answer = db.execute(
        'SELECT * FROM daily_answers WHERE question_id = ? AND user_id = ?',
        (q['id'], partner['id'])
    ).fetchone() if partner else None

    if request.method == 'POST':
        answer = request.form.get('answer', '').strip()
        if answer:
            db.execute(
                'INSERT OR IGNORE INTO daily_answers (question_id, user_id, answer) VALUES (?, ?, ?)',
                (q['id'], session['user_id'], answer)
            )
            db.commit()
            # 重新查询
            my_answer = db.execute(
                'SELECT * FROM daily_answers WHERE question_id = ? AND user_id = ?',
                (q['id'], session['user_id'])
            ).fetchone()

    db.close()

    both_ready = my_answer is not None and partner_answer is not None

    return render_template('daily.html',
                           question=q,
                           my_answer=my_answer,
                           partner=partner,
                           partner_answer=partner_answer,
                           both_ready=both_ready)


# ── 默契大考验 API ──

@app.route('/quiz')
@login_required
def quiz_page():
    db = get_db()
    partner = db.execute(
        'SELECT * FROM users WHERE id != ?', (session['user_id'],)
    ).fetchone()
    db.close()
    return render_template('quiz.html', partner=partner)


@app.route('/api/quiz/status')
@login_required
def quiz_status():
    db = get_db()
    # 找最近的会话
    s = db.execute(
        'SELECT * FROM quiz_sessions ORDER BY id DESC LIMIT 1'
    ).fetchone()

    if not s:
        db.close()
        return jsonify({'has_session': False})

    # 当前用户是否答完了
    my_count = db.execute(
        'SELECT COUNT(*) FROM quiz_answers WHERE session_id = ? AND user_id = ?',
        (s['id'], session['user_id'])
    ).fetchone()[0]

    partner = db.execute(
        'SELECT * FROM users WHERE id != ?', (session['user_id'],)
    ).fetchone()
    partner_count = db.execute(
        'SELECT COUNT(*) FROM quiz_answers WHERE session_id = ? AND user_id = ?',
        (s['id'], partner['id'])
    ).fetchone()[0]

    total_qs = db.execute(
        'SELECT COUNT(*) FROM quiz_answers WHERE session_id = ? GROUP BY question_id',
        (s['id'],)
    ).fetchone()
    total_qs = db.execute(
        'SELECT COUNT(DISTINCT question_id) FROM quiz_answers WHERE session_id = ?',
        (s['id'],)
    ).fetchone()[0]
    # Actually let me get the session question count differently
    session_qs = db.execute(
        'SELECT DISTINCT question_id FROM quiz_answers WHERE session_id = ?',
        (s['id'],)
    ).fetchall()
    total = len(session_qs) if session_qs else 0
    # If no answers yet, check if there's an active session
    if total == 0:
        total = 5  # default

    db.close()

    both_done = my_count >= total and partner_count >= total and total > 0

    return jsonify({
        'has_session': True,
        'session_id': s['id'],
        'my_done': my_count >= total,
        'partner_done': partner_count >= total,
        'both_done': both_done,
        'total_questions': total
    })


@app.route('/api/quiz/start', methods=['POST'])
@login_required
def quiz_start():
    db = get_db()
    # 检查是否有未完成的会话
    s = db.execute(
        'SELECT * FROM quiz_sessions ORDER BY id DESC LIMIT 1'
    ).fetchone()

    if s:
        my_answers = db.execute(
            'SELECT COUNT(*) FROM quiz_answers WHERE session_id = ? AND user_id = ?',
            (s['id'], session['user_id'])
        ).fetchone()[0]
        if my_answers == 0:
            # 有未完成的会话，加入
            db.close()
            return jsonify({'session_id': s['id'], 'joined': True})

    # 创建新会话，随机抽 5 题
    all_qs = db.execute('SELECT id FROM quiz_questions').fetchall()
    selected = random.sample([q['id'] for q in all_qs], min(5, len(all_qs)))

    db.execute('INSERT INTO quiz_sessions DEFAULT VALUES')
    session_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    for qid in selected:
        db.execute(
            'INSERT OR IGNORE INTO quiz_answers (session_id, question_id, user_id, answer) VALUES (?, ?, ?, ?)',
            (session_id, qid, 0, '')  # user_id=0 as placeholder
        )

    db.commit()
    db.close()
    return jsonify({'session_id': session_id, 'joined': False})


@app.route('/api/quiz/questions')
@login_required
def quiz_questions():
    db = get_db()
    session_id = request.args.get('session_id')
    if not session_id:
        db.close()
        return jsonify({'error': 'no session'}), 400

    qids = db.execute(
        'SELECT DISTINCT question_id FROM quiz_answers WHERE session_id = ?',
        (session_id,)
    ).fetchall()

    questions = []
    for row in qids:
        q = db.execute(
            'SELECT * FROM quiz_questions WHERE id = ?', (row['question_id'],)
        ).fetchone()
        my_a = db.execute(
            'SELECT answer FROM quiz_answers WHERE session_id = ? AND question_id = ? AND user_id = ?',
            (session_id, row['question_id'], session['user_id'])
        ).fetchone()
        questions.append({
            'id': q['id'],
            'question': q['question'],
            'category': q['category'],
            'my_answer': my_a['answer'] if my_a else ''
        })

    db.close()
    return jsonify({'questions': questions})


@app.route('/api/quiz/answer', methods=['POST'])
@login_required
def quiz_answer():
    data = request.get_json()
    session_id = data.get('session_id')
    question_id = data.get('question_id')
    answer = data.get('answer', '').strip()

    if not session_id or not question_id or not answer:
        return jsonify({'error': 'missing fields'}), 400

    db = get_db()
    db.execute(
        'INSERT OR REPLACE INTO quiz_answers (session_id, question_id, user_id, answer) VALUES (?, ?, ?, ?)',
        (session_id, question_id, session['user_id'], answer)
    )
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/quiz/results')
@login_required
def quiz_results():
    db = get_db()
    session_id = request.args.get('session_id')
    partner = db.execute(
        'SELECT * FROM users WHERE id != ?', (session['user_id'],)
    ).fetchone()

    qids = db.execute(
        'SELECT DISTINCT question_id FROM quiz_answers WHERE session_id = ? AND user_id > 0',
        (session_id,)
    ).fetchall()

    results = []
    match_count = 0
    for row in qids:
        q = db.execute(
            'SELECT * FROM quiz_questions WHERE id = ?', (row['question_id'],)
        ).fetchone()
        my_a = db.execute(
            'SELECT answer FROM quiz_answers WHERE session_id = ? AND question_id = ? AND user_id = ?',
            (session_id, row['question_id'], session['user_id'])
        ).fetchone()
        p_a = db.execute(
            'SELECT answer FROM quiz_answers WHERE session_id = ? AND question_id = ? AND user_id = ?',
            (session_id, row['question_id'], partner['id'])
        ).fetchone()

        my_text = my_a['answer'] if my_a else ''
        p_text = p_a['answer'] if p_a else ''
        is_match = my_text.strip() == p_text.strip()
        if is_match:
            match_count += 1

        results.append({
            'question': q['question'],
            'category': q['category'],
            'my_answer': my_text,
            'partner_answer': p_text,
            'match': is_match
        })

    total = len(results)
    score = round(match_count / total * 100) if total > 0 else 0

    if score == 100:
        comment = '心有灵犀💯'
    elif score >= 60:
        comment = '还凑合，再接再厉～'
    else:
        comment = '床头吵架床尾和嘛 😂'

    db.close()
    return jsonify({
        'results': results,
        'score': score,
        'comment': comment,
        'match_count': match_count,
        'total': total
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
