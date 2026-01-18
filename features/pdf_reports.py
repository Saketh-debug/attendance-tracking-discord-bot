from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_section_pdf(section_name, rows, date_str, file_path):
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"{section_name.upper()} - Attendance")
    y -= 40

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Serial")
    c.drawString(120, y, "Name")
    c.drawString(300, y, "Status")
    y -= 15

    c.setFont("Helvetica", 11)
    for serial, name, status in rows:
        if y < 50:
            c.showPage()
            y = height - 50

        c.drawString(50, y, str(serial))
        c.drawString(120, y, name)
        c.drawString(300, y, status)
        y -= 15

    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Date: {date_str}")

    c.save()
def generate_student_stats_pdf(rows, file_path):
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Student Attendance Statistics")
    y -= 40

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Name")
    c.drawString(200, y, "Domain")
    c.drawString(300, y, "Attendance %")
    c.drawString(420, y, "Attended")
    c.drawString(500, y, "Total")
    y -= 15

    c.setFont("Helvetica", 11)
    for serial, name, section, total, attended in rows:
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)

        percent = (attended / total * 100) if total else 0

        c.drawString(50, y, name)
        c.drawString(200, y, section)
        c.drawString(320, y, f"{percent:.2f}%")
        c.drawString(440, y, str(attended or 0))
        c.drawString(520, y, str(total or 0))
        y -= 15

    c.save()
