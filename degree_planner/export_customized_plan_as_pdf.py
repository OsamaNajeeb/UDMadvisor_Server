from flask import Blueprint, request, send_file
from fpdf import FPDF
from io import BytesIO

export_customized_plan_to_pdf_blueprint = Blueprint('export_customized_plan_to_pdf', __name__, url_prefix="/api")

@export_customized_plan_to_pdf_blueprint.route('/export_customized_plan_to_pdf', methods=['POST'])
def export_plan():
    data = request.json
    plan = data["plan"]
    semesters = data["plan"]["semesters"]

    # ---------------------------
    # Colors matching <style scoped> in the Vue page
    # ---------------------------
    # Semester header colors (per academic level)
    LEVEL_COLORS = {
        "Freshman": (0x99, 0xD2, 0x4D),   # #99D24D
        "Sophomore": (0x5D, 0xD4, 0xFF),  # #5DD4FF
        "Junior": (0xE8, 0xBC, 0xB4),     # #E8BCB4
        "Senior": (0xB8, 0xA4, 0xC4),     # #B8A4C4
        "Graduate": (0xB5, 0xEB, 0xF2),   # #B5EBF2
    }

    # Status background tints (same as CSS)
    STATUS_BG = {
        "none":        (255, 255, 255),     # white
        "planned":     (0xFF, 0xEB, 0xA8),  # #FFEB A8
        "in progress": (0xA5, 0xDA, 0xFF),  # #A5DAFF
        "completed":   (0xB6, 0xFF, 0xBC),  # #B6FFBC
        "failed":      (255, 189, 199),     # hsl(351,100%,87%) → approx (255,189,199)
        "substituted": (0xF7, 0xC2, 0xFF),  # #F7C2FF
        "waived":      (0xD7, 0xFF, 0xAA),  # #D7FFAA
        "transferred": (0x9F, 0xFF, 0xE2),  # #9FFFE2
    }

    STATUS_ORDER = [
        "planned", "in progress", "completed", "failed",
        "substituted", "waived", "transferred"
    ]

    def norm_status(s: str) -> str:
        if not s:
            return "none"
        s = str(s).strip().lower()
        return s if s in STATUS_BG else "planned"

    def is_completed_like(s: str) -> bool:
        s = (s or "").lower()
        return s in {"completed", "substituted", "waived", "transferred"}

    def label_status(s: str) -> str:
        return s.title()

    def credits_sum(row):
        try:
            return int(row.get("credits", 0))
        except Exception:
            return 0

    class PDF(FPDF):
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=15)
            self.add_page()
            self.set_font("Times", "", 10)
            self.left_x = 10
            self.right_x = 110
            self.page_w = self.w - self.l_margin - self.r_margin
            self.y_start = self.get_y()

        # ---------- header ----------
        def header(self):
            self.set_font("Times", "B", 13)
            title = f"Personalized {plan.get('program','')} Plan"
            self.cell(0, 8, title, ln=True, align="C")
            self.set_font("Times", "", 11)
            sub = f"{plan.get('minor','').strip()} - {plan.get('year','')}".strip(" -")
            if sub:
                self.cell(0, 6, sub, ln=True, align="C")
            self.set_font("Times", "", 10)
            self.multi_cell(0, 6,
                "Use this document to track your degree progress. Verify details with your advisor.",
                align="C"
            )
            self.ln(4)
            self.y_start = self.get_y()

        # ---------- text helpers ----------
        def wrap_text(self, text, max_width, font_size=9):
            self.set_font("Times", "", font_size)
            words = str(text or "").split()
            if not words:
                return [""]
            lines, cur = [], ""
            for w in words:
                t = (cur + " " + w) if cur else w
                if self.get_string_width(t) <= max_width:
                    cur = t
                else:
                    lines.append(cur if cur else w)
                    cur = "" if cur == "" else w
                    if cur == "":
                        # very long word – hard wrap
                        lines.append(w)
            if cur:
                lines.append(cur)
            return lines

        def multi_cell_fixed_height(self, w, h, text, *, strike=False, border=1, align='L', fill=False, font_size=9, text_color=(0,0,0)):
            x0, y0 = self.get_x(), self.get_y()
            line_h = 4
            self.set_font("Times", "", font_size)
            self.set_text_color(*text_color)
            if fill:
                self.rect(x0, y0, w, h, "F")
            if border:
                self.rect(x0, y0, w, h)

            usable_w = w - 2  # small padding
            lines = self.wrap_text(text, usable_w, font_size=font_size)
            total_h = len(lines) * line_h
            y = y0 + max(0, (h - total_h) / 2)
            for ln in lines:
                self.set_xy(x0 + 1, y)
                self.cell(usable_w, line_h, ln, border=0, ln=0, align=align)
                if strike and ln.strip():
                    # strike through the middle of this line
                    tw = min(self.get_string_width(ln), usable_w)
                    y_mid = y + line_h / 2
                    self.line(x0 + 1, y_mid, x0 + 1 + tw, y_mid)
                y += line_h
            # move cursor to the end of the cell
            self.set_xy(x0 + w, y0)

        # ---------- legend ----------
        def draw_status_legend(self):
            self.set_font("Times", "", 9)
            x = self.left_x
            y = self.y_start
            self.set_xy(x, y)
            # self.cell(0, 6, "Color code:", ln=1)
            y = self.get_y()
            box_h, box_w, gap = 5, 5, 4
            cur_x = self.left_x

            items = ["planned", "in progress", "completed", "failed", "substituted", "waived", "transferred"]
            for s in items:
                rgb = STATUS_BG[s]
                label = label_status(s)

                # wrap to next line if needed
                needed = box_w + gap + self.get_string_width(label) + 8
                if cur_x + needed > (self.w - self.r_margin):
                    cur_x = self.left_x
                    y += 8

                # swatch
                self.set_fill_color(*rgb)
                self.rect(cur_x, y, box_w, box_h, "F")
                cur_x += box_w + gap

                # label
                self.set_xy(cur_x, y - 1)  # slight vertical centering
                self.set_text_color(0,0,0)
                self.cell(self.get_string_width(label) + 6, 6, label, ln=0)
                cur_x += self.get_string_width(label) + 10

            self.y_start = y + 10

        # ---------- block drawing ----------
        def semester_block(self, x, y, term_name, courses, header_rgb, credits):
            # dimensions
            W = 90
            self.set_xy(x, y)

            # header
            self.set_fill_color(*header_rgb)
            self.set_font("Times", "B", 10)
            self.cell(W, 8, f"{term_name} ({credits or 0} cr)", border=1, ln=1, fill=True, align="C")

            # table header (yellow)
            self.set_x(x)
            self.set_fill_color(255, 255, 0)
            self.set_font("Times", "B", 9)
            # Status 26 | Course 20 | Title 34 | CR 10
            self.cell(26, 8, "Status", 1, 0, 'C', True)
            self.cell(20, 8, "Course", 1, 0, 'C', True)
            self.cell(34, 8, "Title",  1, 0, 'C', True)
            self.cell(10, 8, "CR",     1, 1, 'C', True)
            self.set_font("Times", "", 9)

            # column widths
            w_status, w_course, w_title, w_cr = 26, 20, 34, 10
            line_h = 4

            for entry in courses:
                if isinstance(entry, dict) and entry.get("type") == "group":
                    s = norm_status(entry.get("status", "none"))
                    bg = STATUS_BG.get(s, STATUS_BG["none"])
                    status_txt = label_status(s)

                    # Build concatenated "OR" title text
                    titles = []
                    options = entry.get("courses", []) or []
                    for opt in options:
                        inner = " + ".join(cc.get("name", "") for cc in opt)
                        titles.append(inner)
                    title_text = "  OR  ".join([t for t in titles if t])

                    # Credits: use explicit group credits if provided, else try to infer only if all numeric and equal
                    group_credits = str(entry.get("credits", "") or "")
                    if not group_credits:
                        # infer (best effort)
                        per_opt = []
                        all_numeric = True
                        for opt in options:
                            total = 0
                            for cc in opt:
                                try:
                                    total += int(cc.get("credits", 0))
                                except Exception:
                                    all_numeric = False
                            per_opt.append(total)
                        if all_numeric and len(set(per_opt)) == 1 and len(per_opt) > 0:
                            group_credits = str(per_opt[0])

                    # compute row height from wrapped title
                    title_lines = self.wrap_text(title_text, w_title - 2)
                    total_lines = max(1, len(title_lines))
                    row_h = max(10, total_lines * line_h + 4)

                    y0 = self.get_y()
                    # background fill for whole row
                    self.set_fill_color(*bg)

                    # Status
                    self.set_xy(x, y0)
                    self.multi_cell_fixed_height(w_status, row_h, status_txt, border=1, align='L', fill=True)

                    # Course (use group tag)
                    self.set_xy(x + w_status, y0)
                    self.multi_cell_fixed_height(w_course, row_h, (entry.get("label") or "Group"), border=1, align='L', fill=True)

                    # Title
                    self.set_xy(x + w_status + w_course, y0)
                    self.multi_cell_fixed_height(w_title, row_h, title_text, border=1, align='L', fill=True)

                    # CR
                    self.set_xy(x + w_status + w_course + w_title, y0)
                    self.multi_cell_fixed_height(w_cr, row_h, group_credits, border=1, align='C', fill=True)

                    self.set_xy(x, y0 + row_h)

                else:
                    # single / elective
                    course = entry
                    s = norm_status(course.get("status", "none"))
                    bg = STATUS_BG.get(s, STATUS_BG["none"])
                    status_txt = label_status(s)

                    subj = course.get("subject", "")
                    num = course.get("number", "")
                    code = (f"{subj} {num}".strip()) if subj != "Elective" else "T/E"
                    title = course.get("name", "")
                    cr = str(course.get("credits", ""))

                    # determine strike
                    strike = is_completed_like(s)

                    # compute row height
                    code_lines  = self.wrap_text(code,  w_course - 2)
                    title_lines = self.wrap_text(title, w_title - 2)
                    total_lines = max(len(code_lines), len(title_lines), 1)
                    row_h = max(10, total_lines * line_h + 4)

                    y0 = self.get_y()
                    self.set_fill_color(*bg)

                    # Status
                    self.set_xy(x, y0)
                    self.multi_cell_fixed_height(w_status, row_h, status_txt, border=1, align='L', fill=True)

                    # Course
                    self.set_xy(x + w_status, y0)
                    self.multi_cell_fixed_height(
                        w_course, row_h, code, border=1, align='L', fill=True,
                        strike=strike, text_color=(80,80,80) if strike else (0,0,0)
                    )

                    # Title
                    self.set_xy(x + w_status + w_course, y0)
                    self.multi_cell_fixed_height(
                        w_title, row_h, title, border=1, align='L', fill=True,
                        strike=strike, text_color=(80,80,80) if strike else (0,0,0)
                    )

                    # CR
                    self.set_xy(x + w_status + w_course + w_title, y0)
                    self.multi_cell_fixed_height(
                        w_cr, row_h, cr, border=1, align='C', fill=True,
                        strike=strike, text_color=(80,80,80) if strike else (0,0,0)
                    )

                    self.set_xy(x, y0 + row_h)

            return self.get_y()

        def estimate_block_height(self, courses):
            total = 8 + 8  # header + table header
            line_h = 4
            w_title = 34

            for entry in courses:
                if isinstance(entry, dict) and entry.get("type") == "group":
                    titles = []
                    options = entry.get("courses", []) or []
                    for opt in options:
                        titles.append(" + ".join(cc.get("name", "") for cc in opt))
                    title_text = "  OR  ".join([t for t in titles if t])
                    title_lines = self.wrap_text(title_text, w_title - 2)
                    total += max(10, len(title_lines) * line_h + 4)
                else:
                    # single
                    code = (f"{entry.get('subject','')} {entry.get('number','')}".strip()
                            if entry.get("subject","") != "Elective" else "T/E")
                    title = entry.get("name","")
                    # approximate by title length (usually the tallest)
                    title_lines = self.wrap_text(title, w_title - 2)
                    code_lines  = self.wrap_text(code,  20 - 2)
                    total += max(10, max(len(title_lines), len(code_lines)) * line_h + 4)

            total += 2
            return total

    pdf = PDF()
    pdf.draw_status_legend()
    pdf.y_start = max(pdf.y_start, pdf.get_y())

    i = 0
    while i < len(semesters):
        sem1 = semesters[i]

        # Summer divider → inline text like your view
        if str(sem1.get("term","")).lower() == "summer":
            label = f"{sem1.get('level','')} Year - Summer"
            items = []
            for c in sem1.get("courses", []):
                if isinstance(c, dict) and c.get("type") == "group":
                    items.append(f"({c.get('label','Group')}) ({c.get('credits','')})")
                else:
                    code = f"{c.get('subject','')} {c.get('number','')}".strip()
                    items.append(f"({code}) ({c.get('credits','')} credits)")
            line = f"{label}: " + ", ".join(items)
            # wrap to next page if needed
            lh = 8 * max(1, len(pdf.wrap_text(line, pdf.page_w)))
            if (pdf.h - pdf.b_margin - pdf.y_start) < lh + 6:
                pdf.add_page()
                pdf.y_start = pdf.get_y()
            pdf.set_xy(pdf.left_x, pdf.y_start)
            pdf.set_font("Times", "B", 10)
            pdf.multi_cell(pdf.page_w, 8, line, align="C")
            pdf.y_start = pdf.get_y() + 6
            i += 1
            continue

        # Non-summer: pair columns when possible
        h1 = pdf.estimate_block_height(sem1.get("courses", []))
        if i + 1 < len(semesters) and str(semesters[i+1].get("term","")).lower() != "summer":
            sem2 = semesters[i+1]
            h2 = pdf.estimate_block_height(sem2.get("courses", []))
            need = max(h1, h2)
            avail = pdf.h - pdf.b_margin - pdf.y_start
            if need > avail:
                pdf.add_page(); pdf.y_start = pdf.get_y()

            t1 = f"{sem1.get('level','')} - {sem1.get('term','')}"
            t2 = f"{sem2.get('level','')} - {sem2.get('term','')}"
            c1 = LEVEL_COLORS.get(sem1.get("level",""), (255,255,255))
            c2 = LEVEL_COLORS.get(sem2.get("level",""), (255,255,255))

            y0 = pdf.y_start
            y1 = pdf.semester_block(pdf.left_x,  y0, t1, sem1.get("courses", []), c1, sem1.get("credits", ""))
            y2 = pdf.semester_block(pdf.right_x, y0, t2, sem2.get("courses", []), c2, sem2.get("credits", ""))
            pdf.y_start = max(y1, y2) + 10
            i += 2
        else:
            # single column
            if h1 > (pdf.h - pdf.b_margin - pdf.y_start):
                pdf.add_page(); pdf.y_start = pdf.get_y()
            t1 = f"{sem1.get('level','')} - {sem1.get('term','')}"
            c1 = LEVEL_COLORS.get(sem1.get("level",""), (255,255,255))
            y1 = pdf.semester_block(pdf.left_x, pdf.y_start, t1, sem1.get("courses", []), c1, sem1.get("credits", ""))
            pdf.y_start = y1 + 10
            i += 1

    out = BytesIO(pdf.output(dest='S').encode('latin1'))
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="academic_plan.pdf", mimetype="application/pdf")
