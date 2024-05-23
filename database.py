import sqlite3
from config import DATABASE_FILE

DATABASE_FILE = 'reservation.db'

def get_connection():
    return sqlite3.connect(DATABASE_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY,
            student_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reservation_date DATE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            team TEXT,
            team_color TEXT
        )
    ''')
    
    # 팀 컬럼이 없는 경우 추가
    c.execute('PRAGMA table_info(users)')
    columns = [column[1] for column in c.fetchall()]
    if 'team' not in columns:
        c.execute('ALTER TABLE users ADD COLUMN team TEXT')
    if 'team_color' not in columns:
        c.execute('ALTER TABLE users ADD COLUMN team_color TEXT')
    
    conn.commit()
    conn.close()

def add_user(student_id, name, password, team, team_color):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO users (student_id, name, password, team, team_color) VALUES (?, ?, ?, ?, ?)",
              (student_id, name, password, team, team_color))
    conn.commit()
    conn.close()

def check_user(student_id, password):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE student_id = ? AND password = ?", (student_id, password))
    user = c.fetchone()
    conn.close()
    return user

def update_user(old_student_id, new_name, new_team, new_student_id, new_team_color):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET name = ?, team = ?, student_id = ?, team_color = ? WHERE student_id = ?", (new_name, new_team, new_student_id, new_team_color, old_student_id))
    conn.commit()
    conn.close()
