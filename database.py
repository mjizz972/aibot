import sqlite3
from datetime import datetime
from config import DB_FILE


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        coins INTEGER DEFAULT 0,
        games_played INTEGER DEFAULT 0,
        games_won INTEGER DEFAULT 0,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        mafia_games INTEGER DEFAULT 0,
        sheriff_games INTEGER DEFAULT 0,
        doctor_games INTEGER DEFAULT 0,
        spy_games INTEGER DEFAULT 0,
        donn_games INTEGER DEFAULT 0,
        last_bonus_date TEXT DEFAULT NULL
    )''')
    # Eski DB ga last_bonus_date qo'shish (migration)
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_bonus_date TEXT DEFAULT NULL")
    except Exception:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        reason TEXT,
        banned_by INTEGER,
        ban_time TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_id INTEGER,
        quantity INTEGER DEFAULT 1,
        UNIQUE(user_id, item_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_id INTEGER,
        earned_date TEXT,
        PRIMARY KEY (user_id, achievement_id)
    )''')
    # Migrations
    for col in [
        "ALTER TABLE users ADD COLUMN win_streak INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_bonus_date TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN custom_title TEXT DEFAULT NULL",
    ]:
        try:
            c.execute(col)
        except Exception:
            pass

    c.execute('''CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        join_time INTEGER DEFAULT 60,
        night_time INTEGER DEFAULT 40,
        discuss_time INTEGER DEFAULT 90,
        vote_time INTEGER DEFAULT 45
    )''')

    for col in [
        "ALTER TABLE users ADD COLUMN bio TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN login_streak INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN last_login_date TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN weekly_bonus_date TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN favorite_role TEXT DEFAULT NULL",
        "ALTER TABLE users ADD COLUMN profile_emoji TEXT DEFAULT '🎭'",
    ]:
        try:
            c.execute(col)
        except Exception:
            pass

    c.execute('''CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER,
        friend_id INTEGER,
        added_date TEXT,
        PRIMARY KEY(user_id, friend_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_missions (
        user_id INTEGER,
        date TEXT,
        games_done INTEGER DEFAULT 0,
        rulet_done INTEGER DEFAULT 0,
        bonus_done INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, date)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS jackpot (
        id INTEGER PRIMARY KEY,
        amount INTEGER DEFAULT 100
    )''')
    c.execute("INSERT OR IGNORE INTO jackpot (id, amount) VALUES (1, 100)")
    c.execute('''CREATE TABLE IF NOT EXISTS group_stats (
        chat_id INTEGER PRIMARY KEY,
        total_games INTEGER DEFAULT 0,
        last_game_date TEXT
    )''')

    conn.commit()
    conn.close()


def ensure_user(user_id: int, name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    c.execute("UPDATE users SET name=? WHERE user_id=?", (name, user_id))
    conn.commit()
    conn.close()


def get_user(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ['user_id', 'name', 'coins', 'games_played', 'games_won', 'kills',
            'deaths', 'mafia_games', 'sheriff_games', 'doctor_games', 'spy_games',
            'donn_games', 'last_bonus_date']
    return dict(zip(keys, row))


def update_stat(user_id: int, **kwargs):
    if not kwargs:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE users SET {key} = {key} + ? WHERE user_id=?", (val, user_id))
    conn.commit()
    conn.close()


def set_stat(user_id: int, **kwargs):
    if not kwargs:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for key, val in kwargs.items():
        c.execute(f"UPDATE users SET {key} = ? WHERE user_id=?", (val, user_id))
    conn.commit()
    conn.close()


def get_top(limit=10) -> list:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT name, games_played, games_won, coins,
               CASE WHEN games_played > 0
               THEN ROUND(games_won * 100.0 / games_played, 1)
               ELSE 0 END as winrate
        FROM users WHERE games_played >= 1
        ORDER BY winrate DESC, games_won DESC, coins DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def is_banned(user_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def ban_user(user_id: int, name: str, reason: str, banned_by: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO banned_users VALUES (?,?,?,?,?)",
              (user_id, name, reason, banned_by, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def unban_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_banned_list() -> list:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id, name, reason, ban_time FROM banned_users")
    rows = c.fetchall()
    conn.close()
    return rows


def get_inventory(user_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT item_id, quantity FROM inventory WHERE user_id=? AND quantity > 0", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{'item_id': r[0], 'quantity': r[1]} for r in rows]


def add_item(user_id: int, item_id: int, qty: int = 1):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO inventory (user_id, item_id, quantity)
                 VALUES (?, ?, ?)
                 ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + ?""",
              (user_id, item_id, qty, qty))
    conn.commit()
    conn.close()


def use_item(user_id: int, item_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=?", (user_id, item_id))
    row = c.fetchone()
    if not row or row[0] <= 0:
        conn.close()
        return False
    c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE user_id=? AND item_id=?",
              (user_id, item_id))
    conn.commit()
    conn.close()
    return True


def has_item(user_id: int, item_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=? AND quantity > 0",
              (user_id, item_id))
    result = c.fetchone()
    conn.close()
    return result is not None


# ==================== DAILY BONUS ====================

def can_claim_bonus(user_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT last_bonus_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return True
    today = datetime.now().strftime("%Y-%m-%d")
    return row[0] != today


def claim_bonus(user_id: int, amount: int = 25) -> bool:
    if not can_claim_bonus(user_id):
        return False
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("UPDATE users SET coins = coins + ?, last_bonus_date = ? WHERE user_id=?",
              (amount, today, user_id))
    conn.commit()
    conn.close()
    return True


# ==================== ACHIEVEMENTS ====================

def get_user_achievements(user_id: int) -> set:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT achievement_id FROM achievements WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return {r[0] for r in rows}


def add_achievement(user_id: int, achievement_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO achievements (user_id, achievement_id, earned_date) VALUES (?,?,?)",
                  (user_id, achievement_id, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False



# ==================== CHAT SETTINGS ====================

def get_chat_settings(chat_id: int) -> dict:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT join_time, night_time, discuss_time, vote_time FROM chat_settings WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'join_time': row[0], 'night_time': row[1], 'discuss_time': row[2], 'vote_time': row[3]}
    return {'join_time': 60, 'night_time': 40, 'discuss_time': 90, 'vote_time': 45}


def update_chat_settings(chat_id: int, **kwargs):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
    for key, val in kwargs.items():
        c.execute(f"UPDATE chat_settings SET {key}=? WHERE chat_id=?", (val, chat_id))
    conn.commit()
    conn.close()


# ==================== COIN TRANSFER ====================

def transfer_coins(from_id: int, to_id: int, amount: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id=?", (from_id,))
    row = c.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return False
    c.execute("UPDATE users SET coins = coins - ? WHERE user_id=?", (amount, from_id))
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, to_id))
    conn.commit()
    conn.close()
    return True


# ==================== WIN STREAK ====================

def update_win_streak(user_id: int, won: bool) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if won:
        c.execute("UPDATE users SET win_streak = win_streak + 1 WHERE user_id=?", (user_id,))
    else:
        c.execute("UPDATE users SET win_streak = 0 WHERE user_id=?", (user_id,))
    c.execute("SELECT win_streak FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row[0] if row else 0


def get_win_streak(user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT win_streak FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


# ==================== KILLS TOP ====================

def get_top_kills(limit: int = 10) -> list:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT name, kills, games_played
        FROM users WHERE kills > 0
        ORDER BY kills DESC, games_played ASC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


# ==================== CUSTOM TITLE ====================

def set_custom_title(user_id: int, title):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET custom_title=? WHERE user_id=?", (title, user_id))
    conn.commit()
    conn.close()


def get_custom_title(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT custom_title FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


# ==================== BIO ====================

def get_bio(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT bio FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def set_bio(user_id: int, bio):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET bio=? WHERE user_id=?", (bio, user_id))
    conn.commit()
    conn.close()


# ==================== LOGIN STREAK ====================

def update_login_streak(user_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT login_streak, last_login_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return 0, False
    streak, last_date = row
    if last_date == today:
        return streak, False
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_date == yesterday:
        new_streak = streak + 1
    else:
        new_streak = 1
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET login_streak=?, last_login_date=? WHERE user_id=?",
              (new_streak, today, user_id))
    conn.commit()
    conn.close()
    return new_streak, True


def get_login_streak(user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT login_streak FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0


# ==================== WEEKLY BONUS ====================

def can_claim_weekly_bonus(user_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT weekly_bonus_date FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row or not row[0]:
        return True
    from datetime import date, timedelta
    last = datetime.strptime(row[0], "%Y-%m-%d").date()
    return (date.today() - last).days >= 7


def claim_weekly_bonus(user_id: int, amount: int = 75) -> bool:
    if not can_claim_weekly_bonus(user_id):
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET coins=coins+?, weekly_bonus_date=? WHERE user_id=?",
              (amount, today, user_id))
    conn.commit()
    conn.close()
    return True


# ==================== FRIENDS ====================

def get_friends(user_id: int) -> list:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT u.user_id, u.name FROM friends f
        JOIN users u ON u.user_id = f.friend_id
        WHERE f.user_id=?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{'user_id': r[0], 'name': r[1]} for r in rows]


def add_friend(user_id: int, friend_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, added_date) VALUES (?,?,?)",
                  (user_id, friend_id, today))
        c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, added_date) VALUES (?,?,?)",
                  (friend_id, user_id, today))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def remove_friend(user_id: int, friend_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM friends WHERE user_id=? AND friend_id=?", (user_id, friend_id))
    c.execute("DELETE FROM friends WHERE user_id=? AND friend_id=?", (friend_id, user_id))
    conn.commit()
    conn.close()


def are_friends(user_id: int, friend_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM friends WHERE user_id=? AND friend_id=?", (user_id, friend_id))
    row = c.fetchone()
    conn.close()
    return row is not None


# ==================== DAILY MISSIONS ====================

def get_daily_missions(user_id: int) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO daily_missions (user_id, date) VALUES (?,?)", (user_id, today))
    conn.commit()
    c.execute("SELECT games_done, rulet_done, bonus_done FROM daily_missions WHERE user_id=? AND date=?",
              (user_id, today))
    row = c.fetchone()
    conn.close()
    if row:
        return {'games_done': row[0], 'rulet_done': row[1], 'bonus_done': row[2], 'date': today}
    return {'games_done': 0, 'rulet_done': 0, 'bonus_done': 0, 'date': today}


def update_daily_mission(user_id: int, field: str, increment: int = 1) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO daily_missions (user_id, date) VALUES (?,?)", (user_id, today))
    c.execute(f"UPDATE daily_missions SET {field} = {field} + ? WHERE user_id=? AND date=?",
              (increment, user_id, today))
    conn.commit()
    conn.close()
    return get_daily_missions(user_id)


# ==================== JACKPOT ====================

def get_jackpot() -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT amount FROM jackpot WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else 100


def add_to_jackpot(amount: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE jackpot SET amount = amount + ? WHERE id=1", (amount,))
    conn.commit()
    conn.close()


def claim_jackpot(winner_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT amount FROM jackpot WHERE id=1")
    row = c.fetchone()
    amount = row[0] if row else 0
    c.execute("UPDATE jackpot SET amount = 100 WHERE id=1")
    if amount > 0:
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id=?", (amount, winner_id))
    conn.commit()
    conn.close()
    return amount


# ==================== GROUP STATS ====================

def get_group_stats(chat_id: int) -> dict:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT total_games, last_game_date FROM group_stats WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'total_games': row[0], 'last_game_date': row[1]}
    return {'total_games': 0, 'last_game_date': None}


def increment_group_games(chat_id: int):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO group_stats (chat_id) VALUES (?)", (chat_id,))
    c.execute("UPDATE group_stats SET total_games=total_games+1, last_game_date=? WHERE chat_id=?",
              (today, chat_id))
    conn.commit()
    conn.close()


# ==================== PROFILE EMOJI ====================

def get_profile_emoji(user_id: int) -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT profile_emoji FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else '🎭'


def set_profile_emoji(user_id: int, emoji: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET profile_emoji=? WHERE user_id=?", (emoji, user_id))
    conn.commit()
    conn.close()


# ==================== FAVORITE ROLE ====================

def get_favorite_role(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT favorite_role FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def set_favorite_role(user_id: int, role: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET favorite_role=? WHERE user_id=?", (role, user_id))
    conn.commit()
    conn.close()


init_db()
