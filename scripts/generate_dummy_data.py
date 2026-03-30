
import psycopg2
import random
from faker import Faker
from datetime import date, timedelta
import sys
import os

# Configuration
DB_NAME = "postgres"
DB_USER = "postgres.fddugbkxyzkjgrzfgcqt"
DB_PASS = "AAC_TECH@4222"
DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
DB_PORT = "6543"

COLLEGES = ["griet", "glec"]
SECTIONS = ["mlops", "webdev", "appdev","dl","iot"]
STUDENTS_PER_COLLEGE = 100
ATTENDANCE_DAYS = 10

fake = Faker()

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        sslmode="require"
    )

def setup_schema(conn):
    cur = conn.cursor()
    print("Setting up schema...")

    # Create colleges table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colleges (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
    """)
    conn.commit()

    # Create sections table if not exists with college_id
    # We will assume 'sections' exists, so we alter it.
    # Check if column exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='sections' AND column_name='college_id';
    """)
    if not cur.fetchone():
        print("Migrating sections table...")
        cur.execute("ALTER TABLE sections ADD COLUMN college_id INT REFERENCES colleges(id) ON DELETE CASCADE;")
        # Fix constraint
        try:
             cur.execute("ALTER TABLE sections DROP CONSTRAINT sections_name_key;")
        except psycopg2.errors.UndefinedObject:
             conn.rollback()
             cur = conn.cursor()
        
        cur.execute("ALTER TABLE sections ADD CONSTRAINT uq_section_college UNIQUE (college_id, name);")
        conn.commit()

    # Create coordinators table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coordinators (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            discord_id TEXT NOT NULL
        );
    """)
    conn.commit()

    # Create students table if not exists
    # Check if college_id exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='students' AND column_name='college_id';
    """)
    if not cur.fetchone():
        print("Migrating students table (college_id)...")
        cur.execute("ALTER TABLE students ADD COLUMN college_id INT REFERENCES colleges(id) ON DELETE CASCADE;")
        conn.commit()

    # Check if coordinator_id exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='students' AND column_name='coordinator_id';
    """)
    if not cur.fetchone():
        print("Migrating students table (coordinator_id)...")
        cur.execute("ALTER TABLE students ADD COLUMN coordinator_id INT REFERENCES coordinators(id) ON DELETE SET NULL;")
        conn.commit()
    
    cur.close()

def clear_data(conn):
    cur = conn.cursor()
    print("Clearing existing data...")
    # Order matters due to FKs
    cur.execute("TRUNCATE TABLE attendance, students, sections, colleges, coordinators RESTART IDENTITY CASCADE;")
    conn.commit()
    cur.close()

def seed_data(conn):
    cur = conn.cursor()
    print("Seeding data...")

    # Insert Colleges
    college_map = {}
    for c in COLLEGES:
        cur.execute("INSERT INTO colleges (name) VALUES (%s) RETURNING id", (c,))
        college_map[c] = cur.fetchone()[0]

    # Insert Coordinators
    coord_ids = []
    for i in range(3):
        cur.execute("INSERT INTO coordinators (name, discord_id) VALUES (%s, %s) RETURNING id", 
                    (fake.name(), f"12345{i}"))
        coord_ids.append(cur.fetchone()[0])
    
    # Sections
    section_map = {c: {} for c in COLLEGES} # college -> section_name -> id

    for c_name in COLLEGES:
        c_id = college_map[c_name]
        for s_name in SECTIONS:
            cur.execute("INSERT INTO sections (name, college_id) VALUES (%s, %s) RETURNING id",
                        (s_name, c_id))
            section_map[c_name][s_name] = cur.fetchone()[0]

    # Students & Attendance
    # GRIET Serial: 1..100
    # GLEC Serial: 1001..1100
    
    # GRIET
    curr_serial = 1
    for _ in range(STUDENTS_PER_COLLEGE):
        c_name = "griet"
        s_name = random.choice(SECTIONS)
        sec_id = section_map[c_name][s_name]
        
        insert_student(cur, curr_serial, c_name, sec_id, college_map[c_name], random.choice(coord_ids))
        curr_serial += 1

    # GLEC
    curr_serial = 1001
    for _ in range(STUDENTS_PER_COLLEGE):
        c_name = "glec"
        s_name = random.choice(SECTIONS)
        sec_id = section_map[c_name][s_name]
        
        insert_student(cur, curr_serial, c_name, sec_id, college_map[c_name], random.choice(coord_ids))
        curr_serial += 1

    conn.commit()
    cur.close()
    print("Done seeding.")

def insert_student(cur, serial, college_name, section_id, college_id, coord_id):
    name = fake.name()
    discord_user = f"{name.replace(' ', '').lower()}_{serial}"
    
    cur.execute("""
        INSERT INTO students (serial_no, name, discord_username, section_id, coordinator_id, college_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (serial, name, discord_user, section_id, coord_id, college_id))

    # Attendance
    today = date.today()
    # Mark random attendance for past 10 days
    # Probability of being Present: 85%
    for i in range(ATTENDANCE_DAYS):
        d = today - timedelta(days=i)
        if d.weekday() >= 5: continue # skip weekends

        status = 'P' if random.random() < 0.85 else 'A'
        cur.execute("""
            INSERT INTO attendance (date, serial_no, status) 
            VALUES (%s, %s, %s)
        """, (d, serial, status))

def main():
    conn = get_conn()
    setup_schema(conn)
    clear_data(conn)
    seed_data(conn)
    conn.close()

if __name__ == "__main__":
    main()
