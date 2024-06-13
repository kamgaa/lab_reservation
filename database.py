import sqlite3
import pandas as pd
from config import DATABASE_FILE

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
    conn.commit()
    conn.close()

def add_user(student_id, name, password, team, team_color):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (student_id, name, password, team, team_color) VALUES (?, ?, ?, ?, ?)",
              (student_id, name, password, team, team_color))
    conn.commit()
    conn.close()

def check_user(student_id, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE student_id = ? AND password = ?", (student_id, password))
    user = c.fetchone()
    conn.close()
    return user

def insert_reservation(student_id, start_time, end_time, reservation_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reservations (student_id, start_time, end_time, reservation_date) VALUES (?, ?, ?, ?)",
              (student_id, start_time, end_time, reservation_date))
    conn.commit()
    conn.close()

def get_reservations():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM reservations", conn)
    conn.close()
    return df

def get_users():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

def insert_users_from_cache(users):
    conn = get_connection()
    c = conn.cursor()
    for user in users:
        c.execute("INSERT INTO users (student_id, name, password, team, team_color) VALUES (?, ?, ?, ?, ?)",
                  (user['student_id'], user['name'], user['password'], user['team'], user['team_color']))
    conn.commit()
    conn.close()

def insert_reservations_from_cache(reservations):
    conn = get_connection()
    c = conn.cursor()
    for reservation in reservations:
        c.execute("INSERT INTO reservations (student_id, start_time, end_time, reservation_date) VALUES (?, ?, ?, ?)",
                  (reservation['student_id'], reservation['start_time'], reservation['end_time'], reservation['reservation_date']))
    conn.commit()
    conn.close()
