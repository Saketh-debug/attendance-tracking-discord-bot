import psycopg2
from datetime import date

conn = psycopg2.connect(
    dbname="attendance_bot",
    user="postgres",
    password="saketh123",
    host="localhost",
    port="5432"
)
def fetch_student_statistics():
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            st.serial_no,
            st.name,
            s.name AS section,
            COUNT(a.id) AS total_classes,
            SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) AS attended
        FROM students st
        JOIN sections s ON st.section_id = s.id
        LEFT JOIN attendance a ON st.serial_no = a.serial_no
        GROUP BY st.serial_no, st.name, s.name
        ORDER BY s.name, st.serial_no;
    """)
    return cur.fetchall()


def fetch_low_attendance(threshold):
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
        GROUP BY st.serial_no, st.name, st.discord_username, s.name
        HAVING 
            CASE 
                WHEN COUNT(a.id) = 0 THEN 0
                ELSE (SUM(CASE WHEN a.status = 'P' THEN 1 ELSE 0 END) * 100.0 / COUNT(a.id))
            END < %s
        ORDER BY s.name, st.name;
    """, (threshold,))
    return cur.fetchall()

def fetch_section_attendance(section_id):
    today = date.today()
    cur = conn.cursor()
    cur.execute("""
        SELECT st.serial_no, st.name, a.status
        FROM students st
        JOIN attendance a ON st.serial_no = a.serial_no
        WHERE st.section_id = %s AND a.date = %s
        ORDER BY st.serial_no
    """, (section_id, today))

    return cur.fetchall(), today

def get_section_id(section_name):
    cur = conn.cursor()
    cur.execute("SELECT id FROM sections WHERE name=%s", (section_name,))
    row = cur.fetchone()
    return row[0] if row else None


def get_students_in_section(section_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT serial_no, name
        FROM students
        WHERE section_id = %s
        ORDER BY serial_no
    """, (section_id,))
    return cur.fetchall()

def mark_attendance(section_id, absentees):
    today = date.today()
    cur = conn.cursor()

    # Get all students in this section
    cur.execute("""
        SELECT serial_no FROM students
        WHERE section_id = %s
    """, (section_id,))
    all_students = [row[0] for row in cur.fetchall()]

    # Validate
    invalid = [s for s in absentees if s not in all_students]
    if invalid:
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
    return True, "Attendance marked successfully."

def fetch_sections():
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM sections ORDER BY name;")
    return cur.fetchall()


def fetch_section_attendance_matrix(section_id):
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
    return cur.fetchall()
