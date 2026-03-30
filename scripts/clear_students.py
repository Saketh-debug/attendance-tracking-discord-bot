import sys
import os

# Add project root to path to import db connection
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import psycopg2
from db import db_pool

def clear_students():
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        print("Clearing all students and attendance records...")
        # CASCADE ensures attendance is cleared when students are cleared.
        # We intentionally do NOT clear colleges, sections, and coordinators.
        cur.execute("TRUNCATE TABLE students, attendance CASCADE;")
        conn.commit()
        cur.close()
        print("Success! Dummy students cleared. Colleges and sections remain intact.")
    except Exception as e:
        print(f"Error clearing data: {e}")
    finally:
        if conn:
            db_pool.putconn(conn)

if __name__ == "__main__":
    clear_students()
