import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import (
    get_college_id, get_section_id, fetch_student_statistics, 
    fetch_section_attendance, fetch_sections, fetch_section_attendance_matrix
)
from features.pdf_reports import generate_section_pdf, generate_student_stats_pdf
from features.excel_export import build_excel

def test_reports():
    print("--- Starting Report Verification ---")
    
    griet_id = get_college_id('griet')
    mlops_id = get_section_id('mlops', griet_id)
    
    # 1. Section PDF
    print("Testing Section PDF...")
    rows, date = fetch_section_attendance(mlops_id)
    if rows:
        generate_section_pdf("mlops", rows, str(date), "test_section_attendance.pdf")
        print("PASS: test_section_attendance.pdf generated.")
    else:
        print("FAIL: No rows for Section PDF.")

    # 2. Student Stats PDF
    print("Testing Student Stats PDF...")
    stats = fetch_student_statistics(griet_id, mlops_id)
    if stats:
        generate_student_stats_pdf(stats, "test_student_stats.pdf")
        print("PASS: test_student_stats.pdf generated.")
    else:
        print("FAIL: No stats for Student Stats PDF.")

    # 3. Excel Export
    print("Testing Excel Export...")
    sections = fetch_sections(griet_id)
    if sections:
        build_excel(sections, fetch_section_attendance_matrix, "test_attendance_master.xlsx")
        print("PASS: test_attendance_master.xlsx generated.")
    else:
        print("FAIL: No sections for Excel Export.")

    print("--- Report Verification Complete ---")

if __name__ == "__main__":
    test_reports()
