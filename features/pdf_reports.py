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
    # --- Column x-positions ---
    COL_NAME      = 50
    COL_ATTENDED  = 310
    COL_TOTAL     = 390
    COL_PERCENT   = 465
    LEFT_MARGIN   = 50
    RIGHT_MARGIN  = 545   # A4 width ≈ 595, leave 50 px right padding
    ROW_HEIGHT    = 16
    DOMAIN_BANNER = 20    # height of the domain header bar

    # Sort: domain name A→Z, then attendance % ascending within each domain
    sorted_rows = sorted(
        rows,
        key=lambda r: (r[2].lower(), (r[4] / r[3] * 100) if r[3] else 0)
    )

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    def draw_column_headers(y_pos):
        """Draw the column header row and return the new y position."""
        c.setFillColorRGB(0.15, 0.15, 0.15)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(COL_NAME,     y_pos, "Name")
        c.drawString(COL_ATTENDED, y_pos, "Attended")
        c.drawString(COL_TOTAL,    y_pos, "Total")
        c.drawString(COL_PERCENT,  y_pos, "Percentage")
        y_pos -= 4
        # Underline
        c.setStrokeColorRGB(0.4, 0.4, 0.4)
        c.setLineWidth(0.5)
        c.line(LEFT_MARGIN, y_pos, RIGHT_MARGIN, y_pos)
        return y_pos - 10

    # --- Page title ---
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(LEFT_MARGIN, y, "Student Attendance Statistics")
    y -= 30

    y = draw_column_headers(y)

    current_section = None
    c.setFont("Helvetica", 11)

    for serial, name, section, total, attended in sorted_rows:
        percent = (attended / total * 100) if total else 0

        # --- Domain group header ---
        if section != current_section:
            current_section = section
            y -= 8  # breathing room above the banner

            # Make sure the banner + at least one data row fit on this page
            if y < (DOMAIN_BANNER + ROW_HEIGHT + 60):
                c.showPage()
                y = height - 50
                y = draw_column_headers(y)
                y -= 8

            # Filled banner spanning full content width
            c.setFillColorRGB(0.2, 0.35, 0.6)   # navy-ish blue
            c.rect(LEFT_MARGIN, y - 4, RIGHT_MARGIN - LEFT_MARGIN, DOMAIN_BANNER,
                   fill=1, stroke=0)

            c.setFillColorRGB(1, 1, 1)            # white text
            c.setFont("Helvetica-Bold", 11)
            c.drawString(LEFT_MARGIN + 6, y + 3, section.upper())

            y -= (DOMAIN_BANNER - 4 + 6)          # move past the banner
            c.setFont("Helvetica", 11)
            c.setFillColorRGB(0, 0, 0)            # reset to black for data rows

        # --- Page break check for data row ---
        if y < 50:
            c.showPage()
            y = height - 50
            y = draw_column_headers(y)
            c.setFont("Helvetica", 11)
            c.setFillColorRGB(0, 0, 0)

        # --- Data row ---
        c.drawString(COL_NAME,     y, name)
        c.drawString(COL_ATTENDED, y, str(attended or 0))
        c.drawString(COL_TOTAL,    y, str(total or 0))
        c.drawString(COL_PERCENT,  y, f"{percent:.2f}%")
        y -= ROW_HEIGHT

    c.save()
