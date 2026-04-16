from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_section_pdf(section_name, rows, date_str, file_path):
    """
    Generates a polished two-column (Present | Absent) attendance PDF.
    Rows: [(serial_no, name, status), ...]
    """
    # --- Layout constants ---
    LEFT_MARGIN  = 40
    RIGHT_MARGIN = 555          # A4 width ≈ 595
    MID_X        = 300          # divider / right-column start
    COL1_X       = LEFT_MARGIN  # Present column text start
    COL2_X       = MID_X + 10  # Absent column text start
    ROW_H        = 16
    HEADER_H     = 22           # height of the green/red column header bar

    present = [r for r in rows if r[2] == 'P']
    absent  = [r for r in rows if r[2] == 'A']
    total   = len(rows)
    pct     = (len(present) / total * 100) if total else 0

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    # ------------------------------------------------------------------ #
    #  Helper: draw the two-column headers (green Present / red Absent)   #
    # ------------------------------------------------------------------ #
    def draw_col_headers(y_pos):
        # Green banner — Present
        c.setFillColorRGB(0.13, 0.55, 0.13)
        c.rect(COL1_X, y_pos - 5, MID_X - COL1_X - 5, HEADER_H, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(COL1_X + 6, y_pos + 3, f"✓  Present  ({len(present)})")

        # Red banner — Absent
        c.setFillColorRGB(0.75, 0.12, 0.12)
        c.rect(COL2_X - 5, y_pos - 5, RIGHT_MARGIN - COL2_X + 5, HEADER_H, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.drawString(COL2_X + 2, y_pos + 3, f"✗  Absent  ({len(absent)})")

        return y_pos - (HEADER_H + 4)

    # ------------------------------------------------------------------ #
    #  PAGE 1: Title banner + summary stats bar                           #
    # ------------------------------------------------------------------ #
    y = height - 40

    # --- Title banner ---
    c.setFillColorRGB(0.12, 0.22, 0.45)   # dark navy
    c.rect(LEFT_MARGIN, y - 6, RIGHT_MARGIN - LEFT_MARGIN, 30, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(LEFT_MARGIN + 8, y + 4, f"{section_name.upper()}  —  Attendance Report")
    y -= 40

    # --- Date line ---
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont("Helvetica", 10)
    c.drawString(LEFT_MARGIN, y, f"Date: {date_str}")
    y -= 22

    # --- Summary stats bar ---
    box_w  = (RIGHT_MARGIN - LEFT_MARGIN) / 4 - 4
    stats  = [
        ("Total Students", str(total),          (0.20, 0.20, 0.20)),
        ("Present",        str(len(present)),   (0.13, 0.55, 0.13)),
        ("Absent",         str(len(absent)),    (0.75, 0.12, 0.12)),
        ("Attendance %",   f"{pct:.1f}%",       (0.15, 0.35, 0.65)),
    ]
    bx = LEFT_MARGIN
    for label, value, colour in stats:
        r, g, b = colour
        c.setFillColorRGB(r, g, b)
        c.roundRect(bx, y - 24, box_w, 40, 4, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(bx + box_w / 2, y + 4, value)
        c.setFont("Helvetica", 8)
        c.drawCentredString(bx + box_w / 2, y - 14, label)
        bx += box_w + 5
    y -= 50

    # --- Thin separator ---
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    c.line(LEFT_MARGIN, y, RIGHT_MARGIN, y)
    y -= 14

    # --- Column headers ---
    y = draw_col_headers(y)
    y -= 6

    # ------------------------------------------------------------------ #
    #  Data rows — two-column, alternating shading                        #
    # ------------------------------------------------------------------ #
    c.setFont("Helvetica", 10)
    max_len = max(len(present), len(absent), 1)

    for i in range(max_len):
        # Page break — reprint column headers
        if y < 55:
            c.showPage()
            y = height - 40
            # Compact repeat header
            c.setFillColorRGB(0.12, 0.22, 0.45)
            c.rect(LEFT_MARGIN, y - 6, RIGHT_MARGIN - LEFT_MARGIN, 22, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(LEFT_MARGIN + 8, y + 2,
                         f"{section_name.upper()}  —  {date_str}  (continued)")
            y -= 36
            y = draw_col_headers(y)
            y -= 6
            c.setFont("Helvetica", 10)

        # Alternating row background
        if i % 2 == 0:
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(LEFT_MARGIN, y - 3, RIGHT_MARGIN - LEFT_MARGIN, ROW_H,
                   fill=1, stroke=0)

        # Centre divider
        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.setLineWidth(0.4)
        c.line(MID_X, y - 3, MID_X, y + ROW_H - 3)

        # Present entry
        if i < len(present):
            s_no, name, _ = present[i]
            c.setFillColorRGB(0.10, 0.10, 0.10)
            c.drawString(COL1_X + 4, y, f"{s_no}.  {name}")

        # Absent entry
        if i < len(absent):
            s_no, name, _ = absent[i]
            c.setFillColorRGB(0.55, 0.05, 0.05)   # dark red for absent names
            c.drawString(COL2_X + 2, y, f"{s_no}.  {name}")

        c.setFillColorRGB(0, 0, 0)
        y -= ROW_H

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
