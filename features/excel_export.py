import pandas as pd

def build_excel(sections, fetch_func, file_path):
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        for section_id, section_name in sections:
            rows = fetch_func(section_id)

            if not rows:
                continue

            df = pd.DataFrame(rows, columns=["Serial", "Name", "Date", "Status"])

            # Pivot: rows -> students, columns -> dates
            pivot = df.pivot_table(
                index=["Serial", "Name"],
                columns="Date",
                values="Status",
                aggfunc="first"
            ).reset_index()

            pivot.to_excel(writer, sheet_name=section_name, index=False)
