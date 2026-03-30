import csv
import psycopg2
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import db_pool

def import_students_from_csv(csv_filepath):
    conn = None
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        
        print(f"Reading from {csv_filepath}...")
        success_count = 0
        skip_count = 0

        with open(csv_filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Verify required headers
            required = {'serial_no', 'name', 'section', 'college'}
            headers = set(reader.fieldnames or [])
            if not required.issubset(headers):
                print(f"Error: CSV is missing required columns. Requires: {required}")
                return

            for row in reader:
                serial = row['serial_no'].strip()
                name = row['name'].strip()
                discord_user = row.get('discord_username', '').strip()
                if not discord_user:
                    discord_user = None
                    
                section_name = row['section'].strip().lower()
                college_name = row['college'].strip().lower()
                
                # 1. Get College ID
                cur.execute("SELECT id FROM colleges WHERE name=%s", (college_name,))
                college_res = cur.fetchone()
                if not college_res:
                    print(f"Skipping '{name}' (Serial {serial}): College '{college_name}' not found.")
                    skip_count += 1
                    continue
                college_id = college_res[0]
                
                # 2. Get Section ID
                cur.execute("SELECT id FROM sections WHERE name=%s AND college_id=%s", (section_name, college_id))
                section_res = cur.fetchone()
                if not section_res:
                    print(f"Skipping '{name}' (Serial {serial}): Section '{section_name}' not found in {college_name}.")
                    skip_count += 1
                    continue
                section_id = section_res[0]

                # 3. Insert Student
                try:
                    cur.execute("""
                        INSERT INTO students (serial_no, name, discord_username, section_id, college_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (serial_no) DO NOTHING;
                    """, (serial, name, discord_user, section_id, college_id))
                    success_count += 1
                except Exception as e:
                    print(f"Error inserting {name}: {e}")
                    conn.rollback()
                    skip_count += 1
                    cur = conn.cursor() # reset cursor after rollback
                
        conn.commit()
        cur.close()
        print(f"Import complete! Successfully inserted {success_count} students. Skipped {skip_count} due to errors/duplicates.")
        
    except Exception as ex:
        print(f"Fatal error during import: {ex}")
    finally:
        if conn:
            db_pool.putconn(conn)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_csv.py <path_to_csv_file>")
        print("Example: python scripts/import_csv.py glec_students.csv")
        sys.exit(1)
        
    csv_path = sys.argv[1]
    if os.path.exists(csv_path):
        import_students_from_csv(csv_path)
    else:
        print(f"Error: File not found: {csv_path}")
