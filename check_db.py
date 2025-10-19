
import sqlite3

def check_db():
    try:
        conn = sqlite3.connect("backend/data/headlines.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM headlines")
        count = cursor.fetchone()[0]
        print(f"Number of rows in headlines table: {count}")
        conn.close()
    except sqlite3.Error as e:
        print(f"Error accessing database: {e}")

if __name__ == "__main__":
    check_db()
