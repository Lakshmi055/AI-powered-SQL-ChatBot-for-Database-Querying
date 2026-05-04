from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime


def generate_pdf(chat_history):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    # Title
    elements.append(Paragraph("<b>AI SQL Chat Report</b>", styles["Title"]))
    elements.append(Paragraph(
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 20))

    for i in range(0, len(chat_history), 3):
        try:
            user_q = chat_history[i]["content"]
            sql_q = chat_history[i+1]["content"]

            columns = chat_history[i+2].get("columns", [])
            rows = chat_history[i+2].get("rows", [])

            # Question
            elements.append(Paragraph(f"<b>Question:</b> {user_q}", styles["Normal"]))
            elements.append(Spacer(1, 8))

            # SQL
            elements.append(Paragraph(f"<b>SQL:</b> {sql_q}", styles["Normal"]))
            elements.append(Spacer(1, 10))

            # Table
            if columns:
                # ✅ FIX: convert dict rows → list rows
                if rows and isinstance(rows[0], dict):
                    table_rows = [[row.get(col, "") for col in columns] for row in rows]
                else:
                    table_rows = rows

                table_data = [columns] + table_rows

                table = Table(table_data)

                table.setStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ])

                elements.append(table)

            elements.append(Spacer(1, 20))

        except Exception as e:
            print("PDF error:", e)
            continue

    doc.build(elements)
    buffer.seek(0)
    return buffer