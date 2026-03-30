import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import (
    get_college_id, get_section_id, fetch_student_statistics, 
    fetch_low_attendance, fetch_section_attendance, mark_attendance
)

def test_verification():
    print("--- Starting Verification ---")
    
    # 1. Test College ID
    griet_id = get_college_id('griet')
    glec_id = get_college_id('glec')
    print(f"GRIET ID: {griet_id}, GLEC ID: {glec_id}")
    
    if not griet_id or not glec_id:
        print("FAIL: Colleges not found.")
        return

    # 2. Test Section ID (Context Aware)
    # Looking for 'mlops' in GRIET
    mlops_griet = get_section_id('mlops', griet_id)
    print(f"MLOps (GRIET) ID: {mlops_griet}")
    
    # Looking for 'mlops' in GLEC
    mlops_glec = get_section_id('mlops', glec_id)
    print(f"MLOps (GLEC) ID: {mlops_glec}")
    
    if mlops_griet == mlops_glec:
        print("FAIL: MLOps section IDs should be different for different colleges.")
    else:
        print("PASS: Section IDs are distinct.")

    # 3. Test Student Stats (College Scoped)
    stats_griet = fetch_student_statistics(griet_id, mlops_griet)
    print(f"Stats GRIET MLOps count: {len(stats_griet)}")
    
    if len(stats_griet) == 0:
        print("WARN: No students found for GRIET MLOps. Did seeding work?")
    else:
        print(f"Sample Student: {stats_griet[0]}")

    # 4. Test Mark Attendance
    # Pick a student serial from GRIET MLOps
    # Assuming serials 1-100 are GRIET as per seed script (if logic held)
    # Let's verify via stats
    if stats_griet:
        student_serial = stats_griet[0][0] # serial is first col
        print(f"Marking attendance for student serial: {student_serial} in section {mlops_griet}")
        
        # Mark absentee
        success, msg = mark_attendance(mlops_griet, [student_serial])
        print(f"Mark Attendance Result: {success} - {msg}")
        
        # Verify status
        rows, date = fetch_section_attendance(mlops_griet)
        # Find our student
        status = next((r[2] for r in rows if r[0] == student_serial), "Unknown")
        print(f"Student {student_serial} status today: {status}")
        
        if status == 'A':
            print("PASS: Student correctly marked Absent.")
        else:
            print("FAIL: Student status not Absent.")

    print("--- Verification Complete ---")

if __name__ == "__main__":
    test_verification()
