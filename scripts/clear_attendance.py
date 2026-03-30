import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import db_pool

def clear_attendance():
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        print("Clearing all attendance records...")
        cur.execute("TRUNCATE TABLE attendance;")
        conn.commit()
        cur.close()
        print("Success! All attendance data has been wiped. Students, sections, and colleges remain intact.")
    except Exception as e:
        print(f"Error clearing attendance: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

if __name__ == "__main__":
    clear_attendance()
