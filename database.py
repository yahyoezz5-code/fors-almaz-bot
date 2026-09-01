import sqlite3

def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            spent REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()

def add_balance(user_id: int, amount: float):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (user_id, balance) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    ''', (user_id, amount, amount))
    conn.commit()
    conn.close()

def process_purchase(user_id: int, price: float) -> bool:
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < price:
        conn.close()
        return False

    new_balance = row[0] - price
    cursor.execute("UPDATE users SET balance = ?, spent = spent + ? WHERE user_id = ?", (new_balance, price, user_id))
    conn.commit()
    conn.close()
    return True