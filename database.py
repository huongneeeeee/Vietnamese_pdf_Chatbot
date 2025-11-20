import sqlite3
from datetime import datetime

DB_NAME = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Bảng lịch sử chat
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_query TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Bảng danh sách sessions
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. [MỚI] Bảng liên kết Session - File
    # Bảng này giúp nhớ: Session A có những file nào.
    c.execute('''
        CREATE TABLE IF NOT EXISTS session_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# --- CÁC HÀM CHO SESSION FILES ---
def add_file_to_session(session_id, filename, file_path):
    """Gắn một file vào session cụ thể"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Kiểm tra xem file đã có trong session này chưa để tránh trùng
    c.execute("SELECT id FROM session_files WHERE session_id = ? AND filename = ?", (session_id, filename))
    if c.fetchone() is None:
        c.execute("INSERT INTO session_files (session_id, filename, file_path) VALUES (?, ?, ?)", 
                  (session_id, filename, file_path))
    conn.commit()
    conn.close()

def get_files_by_session(session_id):
    """Lấy danh sách file của một session"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT filename FROM session_files WHERE session_id = ?", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [row['filename'] for row in rows]

def remove_file_from_session(session_id, filename):
    """Gỡ file khỏi session (nhưng không xóa file gốc trên đĩa nếu session khác đang dùng)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM session_files WHERE session_id = ? AND filename = ?", (session_id, filename))
    conn.commit()
    conn.close()

def delete_session(session_id):
    """Xóa toàn bộ dữ liệu của session"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM session_files WHERE session_id = ?", (session_id,)) # Xóa liên kết file
    conn.commit()
    conn.close()

# --- CÁC HÀM CŨ (GIỮ NGUYÊN) ---
def save_message(session_id, user_query, bot_response):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    if c.fetchone() is None:
        short_title = (user_query[:47] + '...') if len(user_query) > 47 else user_query
        c.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, short_title))
    c.execute("INSERT INTO history (session_id, user_query, bot_response) VALUES (?, ?, ?)",
              (session_id, user_query, bot_response))
    conn.commit()
    conn.close()

def get_history(session_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT user_query, bot_response FROM history WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    history = []
    for row in rows:
        history.append({"role": "user", "content": row["user_query"]})
        history.append({"role": "bot", "content": row["bot_response"]})
    return history

def get_all_sessions():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"session_id": row["session_id"], "title": row["title"]} for row in rows]

def clear_history(session_id):
    delete_session(session_id)

init_db()