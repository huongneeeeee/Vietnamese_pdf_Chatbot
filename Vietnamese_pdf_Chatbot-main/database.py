import sqlite3
from datetime import datetime

DB_NAME = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. Bảng lưu nội dung chat (chi tiết)
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            user_query TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Bảng lưu danh sách các phiên chat (Sessions)
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_message(session_id, user_query, bot_response):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Kiểm tra xem session này đã tồn tại chưa
    c.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    if c.fetchone() is None:
        # Nếu chưa, tạo session mới và lấy câu hỏi đầu tiên làm tiêu đề (giới hạn 50 ký tự)
        short_title = (user_query[:47] + '...') if len(user_query) > 47 else user_query
        c.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, short_title))
    
    # Lưu tin nhắn
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
    """Lấy danh sách tất cả các cuộc trò chuyện, sắp xếp mới nhất lên đầu"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT session_id, title FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"session_id": row["session_id"], "title": row["title"]} for row in rows]

def delete_session(session_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def clear_history(session_id):
    """
    Hàm này để tương thích với app.py đang gọi db.clear_history.
    Nó sẽ thực hiện việc xóa session giống như delete_session.
    """
    delete_session(session_id)

# Chạy khởi tạo DB
init_db()