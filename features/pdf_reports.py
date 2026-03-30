from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_section_pdf(section_name, rows, date_str, file_path):
    # Rows: [(serial, name, status), ...]
    # We want two columns: Present List | Absent List
    present = [r for r in rows if r[2] == 'P']
    absent = [r for r in rows if r[2] == 'A']
    
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"{section_name.upper()} - Attendance ({date_str})")
    y -= 40
    
    # Grid Layout
    # Left: Present, Right: Absent
    col1_x = 50
    col2_x = 300
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(col1_x, y, f"Present ({len(present)})")
    c.drawString(col2_x, y, f"Absent ({len(absent)})")
    y -= 20
    
    c.setFont("Helvetica", 10)
    
    # Determine max rows to iterate
    max_len = max(len(present), len(absent))
    
    start_y = y
    
    for i in range(max_len):
        if y < 50:
            c.showPage()
            y = height - 50
            # Header again? Optional.
            c.setFont("Helvetica", 10)

        # Present Name
        if i < len(present):
            s_no, name, _ = present[i]
            c.drawString(col1_x, y, f"{s_no}. {name}")
            
        # Absent Name
        if i < len(absent):
            s_no, name, _ = absent[i]
            c.drawString(col2_x, y, f"{s_no}. {name}")
            
        y -= 15

    c.save()

def generate_student_stats_pdf(rows, file_path):
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Student Attendance Statistics")
    y -= 40

    c.setFont("Helvetica-Bold", 11)
    # Columns: Name, Classes Attended, Total Classes, Attendance %
    c.drawString(50, y, "Name")
    c.drawString(250, y, "Attended")
    c.drawString(350, y, "Total")
    c.drawString(450, y, "Percentage")
    y -= 15

    c.setFont("Helvetica", 11)
    # rows: serial, name, section, total, attended
    for serial, name, section, total, attended in rows:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

        percent = (attended / total * 100) if total else 0

        c.drawString(50, y, f"{name} ({section})") # Including section in name col for better context if mixed
        c.drawString(250, y, str(attended or 0))
        c.drawString(350, y, str(total or 0))
        c.drawString(450, y, f"{percent:.2f}%")
        y -= 15

    c.save()
