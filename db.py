import psycopg2
from psycopg2 import pool
from datetime import date
import os
from dotenv import load_dotenv
import sys

# Resolve .env path (same logic as config.py so it works both as script and packaged exe)
if getattr(sys, 'frozen', False):
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    bundled_env = os.path.join(bundle_dir, '.env')
    exe_dir = os.path.dirname(sys.executable)
    external_env = os.path.join(exe_dir, '.env')
    env_path = external_env if os.path.exists(external_env) else bundled_env
else:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

load_dotenv(dotenv_path=env_path)

db_pool = pool.SimpleConnectionPool(
    1, 20,
    dbname=os.getenv("DB_NAME", "postgres"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT", "6543"),
    sslmode="require"
)

def get_college_id(college_name):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM colleges WHERE name=%s", (college_name,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        db_pool.putconn(conn)

def fetch_student_statistics(college_id, section_id=None):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        query = """
            SELECT 
                st.serial_no,
                st.name,
                s.name AS section,
                COUNT(a.id) AS total_classes,
                SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) AS attended
            FROM students st
            JOIN sections s ON st.section_id = s.id
            LEFT JOIN attendance a ON st.serial_no = a.serial_no
            WHERE st.college_id = %s
        """
        params = [college_id]
        
        if section_id:
            query += " AND st.section_id = %s"
            params.append(section_id)
            
        query += " GROUP BY st.serial_no, st.name, s.name ORDER BY s.name, st.serial_no;"
        
        cur.execute(query, tuple(params))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def fetch_low_attendance(threshold, section_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                st.name,
                st.discord_username,
                s.name AS section,
                COUNT(a.id) AS total_classes,
                SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) AS attended
            FROM students st
            JOIN sections s ON st.section_id = s.id
            LEFT JOIN attendance a ON st.serial_no = a.serial_no
            WHERE st.section_id = %s
            GROUP BY st.serial_no, st.name, st.discord_username, s.name
            HAVING 
                CASE 
                    WHEN COUNT(a.id) = 0 THEN 0
                    ELSE (SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.id))
                END < %s
            ORDER BY s.name, st.name;
        """, (section_id, threshold))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def fetch_low_attendance_all(threshold, college_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                st.name,
                st.discord_username,
                s.name AS section,
                COUNT(a.id) AS total_classes,
                SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) AS attended
            FROM students st
            JOIN sections s ON st.section_id = s.id
            LEFT JOIN attendance a ON st.serial_no = a.serial_no
            WHERE st.college_id = %s
            GROUP BY st.serial_no, st.name, st.discord_username, s.name
            HAVING 
                CASE 
                    WHEN COUNT(a.id) = 0 THEN 0
                    ELSE (SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.id))
                END < %s
            ORDER BY s.name, st.name;
        """, (college_id, threshold))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def fetch_section_attendance(section_id):
    today = date.today()
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT st.serial_no, st.name, a.status
            FROM students st
            LEFT JOIN attendance a ON st.serial_no = a.serial_no AND a.date = %s
            WHERE st.section_id = %s
            ORDER BY st.serial_no
        """, (today, section_id))
        res = cur.fetchall()
        cur.close()
        return res, today
    finally:
        db_pool.putconn(conn)

def get_section_id(section_name, college_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM sections WHERE name=%s AND college_id=%s", (section_name, college_id))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        db_pool.putconn(conn)

def get_students_in_section(section_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT serial_no, name
            FROM students
            WHERE section_id = %s
            ORDER BY serial_no
        """, (section_id,))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def mark_attendance(section_id, absentees):
    today = date.today()
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        # Get all students in this section
        cur.execute("""
            SELECT serial_no FROM students
            WHERE section_id = %s
        """, (section_id,))
        all_students_rows = cur.fetchall()
        all_students = [row[0] for row in all_students_rows]
        
        if not all_students:
            cur.close()
            return False, "No students found in this section."

        # Validate
        invalid = [s for s in absentees if s not in all_students]
        if invalid:
            cur.close()
            return False, f"Invalid serial numbers for this domain: {invalid}. You might have entered the serial number that belongs to an other domain."

        # Insert all as Present
        for s in all_students:
            cur.execute("""
                INSERT INTO attendance (date, serial_no, status)
                VALUES (%s, %s, 'P')
                ON CONFLICT (date, serial_no)
                DO UPDATE SET status='P'
            """, (today, s))

        # Mark absentees
        for s in absentees:
            cur.execute("""
                UPDATE attendance
                SET status='A'
                WHERE date=%s AND serial_no=%s
            """, (today, s))

        conn.commit()
        cur.close()
        return True, "Attendance marked successfully."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        db_pool.putconn(conn)

def fetch_sections(college_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM sections WHERE college_id=%s ORDER BY name;", (college_id,))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def fetch_section_attendance_matrix(section_id):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                st.serial_no,
                st.name,
                a.date,
                a.status
            FROM students st
            LEFT JOIN attendance a ON st.serial_no = a.serial_no
            WHERE st.section_id = %s
            ORDER BY st.serial_no, a.date;
        """, (section_id,))
        res = cur.fetchall()
        cur.close()
        return res
    finally:
        db_pool.putconn(conn)

def get_student_coordinator(discord_username):
    conn = db_pool.getconn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.discord_id 
            FROM students s
            JOIN coordinators c ON s.coordinator_id = c.id
            WHERE s.discord_username = %s
        """, (discord_username,))
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    finally:
        db_pool.putconn(conn)
