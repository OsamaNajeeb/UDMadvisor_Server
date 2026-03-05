from flask import Blueprint, request, send_file
from fpdf import FPDF
from io import BytesIO
from collections import OrderedDict

export_plan_blueprint = Blueprint('export_plan_to_pdf', __name__, url_prefix="/api")

@export_plan_blueprint.route('/export_plan_to_pdf', methods=['POST'])
def export_plan():
    data = request.json
    plan = data["plan"]
    semesters = data["plan"]["semesters"]

    PALETTE = [
        (31, 78, 121),  # Navy
        (0, 109, 91),   # Teal
        (139, 0, 0),    # Maroon
        (94, 42, 126),  # Purple
        (179, 87, 0),   # Orange
        (47, 79, 79),   # Slate
        (31, 119, 180)  # Blue
    ]

    level_colors = {
        "Freshman": (180, 237, 180),
        "Sophomore": (173, 216, 230),
        "Junior": (255, 204, 204),
        "Senior": (230, 230, 230)
    }

    def collect_labels(semesters):
        labels = []
        for sem in semesters:
            for c in sem.get("courses", []):
                if isinstance(c, dict) and c.get("type") == "group":
                    lab = c.get("label", "No Label") or "No Label"
                    if lab not in labels:
                        labels.append(lab)
                else:
                    lab = c.get("label", "No Label") or "No Label"
                    if lab not in labels:
                        labels.append(lab)
        return labels

    labels = collect_labels(semesters)
    label_colors = OrderedDict()
    for idx, lab in enumerate(labels):
        if lab.lower() == "no label":
            label_colors[lab] = (0, 0, 0)
        elif idx < len(PALETTE):
            label_colors[lab] = PALETTE[idx]
        else:
            label_colors[lab] = PALETTE[idx % len(PALETTE)]

    def compute_semester_credits(courses):
        credits_list = []
        for entry in courses:
            if isinstance(entry, dict) and entry.get("type") == "group":
                options = entry.get("courses", [])
                option_sums = []
                for opt in options:
                    total = 0
                    for c in opt:
                        try:
                            total += int(c.get("credits", 0))
                        except Exception:
                            pass
                    option_sums.append(total)
                if option_sums:
                    if len(set(option_sums)) == 1:
                        credits_list.append(option_sums[0])
                    else:
                        credits_list.append(f"{min(option_sums)}-{max(option_sums)}")
            else:
                try:
                    credits_list.append(int(entry.get("credits", 0)))
                except Exception:
                    pass

        nums = [c for c in credits_list if isinstance(c, int)]
        ranges = [c for c in credits_list if isinstance(c, str)]
        if nums and not ranges:
            return sum(nums)
        elif nums and ranges:
            return f"{sum(nums)} + " + " + ".join(ranges)
        elif ranges:
            return " + ".join(ranges)
        else:
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
            self.set_text_color(0, 0, 0)

        def header(self):
            self.set_font("Times", "B", 13)
            self.cell(0, 8, f"{data['plan']['program']} - {data['plan']['year']}", ln=True, align="C")
            if data['plan'].get('minor'):
                self.set_font("Times", "B", 11)
                self.cell(0, 8, f"{data['plan']['minor']}", ln=True, align="C")
            self.set_font("Times", "", 10)
            self.ln(6)
            self.y_start = self.get_y()
            self.set_text_color(0, 0, 0)

        def truncate_text(self, text, max_width, font_size=9):
            self.set_font("Times", "", font_size)
            if self.get_string_width(text) <= max_width:
                return text
            left, right = 0, len(text)
            while left < right:
                mid = (left + right + 1) // 2
                test_text = text[:mid] + "..."
                if self.get_string_width(test_text) <= max_width:
                    left = mid
                else:
                    right = mid - 1
            return (text[:left] + "...") if left > 0 else "..."

        def wrap_text(self, text, max_width, font_size=9):
            self.set_font("Times", "", font_size)
            if self.get_string_width(text) <= max_width:
                return [text]
            words = str(text).split()
            lines, current_line = [], ""
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if self.get_string_width(test_line) <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(self.truncate_text(word, max_width, font_size))
            if current_line:
                lines.append(current_line)
            return lines

        def multi_cell_fixed_height(self, w, h, text, border=0, align='L', fill=False):
            x, y = self.get_x(), self.get_y()
            line_height = 4
            available_width = w - 2
            lines = self.wrap_text(text, available_width)
            total_text_height = len(lines) * line_height
            text_y = y + max(0, (h - total_text_height) / 2)
            if fill:
                self.rect(x, y, w, h, 'F')
            if border:
                self.rect(x, y, w, h)
            for line in lines:
                self.set_xy(x + 1, text_y)
                self.cell(w - 2, line_height, line, border=0, ln=0, align=align)
                text_y += line_height
            self.set_xy(x + w, y)

        def draw_legend(self, labels_colors):
            if not labels_colors:
                return getattr(self, "y_start", self.get_y())
            x = self.left_x
            y = getattr(self, "y_start", self.get_y())
            line_h = 8
            self.set_xy(x, y)
            self.set_font("Times", "", 9)
            prefix = "Legend: "
            self.cell(self.get_string_width(prefix), line_h, prefix, border=0, ln=0)
            cur_x = x + self.get_string_width(prefix) + 3
            page_right = self.w - self.r_margin
            first = True
            for lab, col in labels_colors.items():
                label_text = str(lab)
                text_w = self.get_string_width(label_text) + 6
                item_w = text_w + (8 if not first else 0)
                if cur_x + item_w > page_right:
                    y += line_h
                    self.set_xy(self.left_x, y)
                    cur_x = self.left_x
                if not first:
                    self.set_x(cur_x + 3)
                self.set_xy(cur_x, y)
                self.set_text_color(*col)
                max_label_w = page_right - cur_x - 4
                label_lines = self.wrap_text(label_text, max_label_w)
                draw_text = label_lines[0] if label_lines else label_text
                self.cell(max_label_w, line_h, draw_text, border=0, ln=0)
                cur_x += self.get_string_width(draw_text) + 4
                self.set_text_color(0, 0, 0)
                first = False
            bottom_y = y + line_h + 2
            self.y_start = bottom_y
            return bottom_y

        def semester_block(self, x, y, term_name, courses, bg_color, credits):
            self.set_xy(x, y)
            self.set_fill_color(*bg_color)
            self.set_font("Times", "B", 10)
            self.cell(90, 8, f"{term_name}", border=1, ln=1, fill=True, align="C")
            self.set_x(x)
            self.set_fill_color(255, 255, 0)
            self.set_font("Times", "B", 9)
            self.cell(20, 8, "Course", 1, 0, 'C', True)
            self.cell(55, 8, "Title", 1, 0, 'C', True)
            self.cell(15, 8, "CR", 1, 1, 'C', True)
            self.set_font("Times", "", 9)
            self.set_text_color(0, 0, 0)

            w_course, w_title, w_cr, pad = 20, 55, 15, 2
            max_w_course = w_course - pad
            max_w_title = w_title - pad

            for entry in courses:
                if isinstance(entry, dict) and entry.get("type") == "group":
                    group = entry
                    group_label = group.get("label", "No Label") or "No Label"
                    row_color = label_colors.get(group_label, (0, 0, 0))
                    options = group.get("courses", [])
                    option_titles, option_credits, numeric_sums = [], [], []
                    for opt in options:
                        titles, total_credits, numeric = [], 0, True
                        for cc in opt:
                            titles.append(cc.get("name", ""))
                            try:
                                total_credits += int(cc.get("credits", 0))
                            except Exception:
                                numeric = False
                        option_titles.append(" + ".join(titles))
                        option_credits.append(str(total_credits) if numeric else "")
                        numeric_sums.append(numeric)
                    title_text = "  OR  ".join(option_titles)
                    group_credits_raw = group.get("credits", "")
                    if group_credits_raw:
                        credits_text = str(group_credits_raw)
                    else:
                        if all(numeric_sums) and len(set(option_credits)) == 1:
                            credits_text = option_credits[0]
                        else:
                            credits_text = ""
                    title_lines = self.wrap_text(title_text, max_w_title)
                    total_lines = max(1, len(title_lines))
                    line_h = 4
                    row_height = max(10, total_lines * line_h + 4)
                    current_y = self.get_y()
                    self.set_xy(x, current_y)
                    self.set_text_color(*row_color)
                    self.multi_cell_fixed_height(w_course, row_height, group_label, border=1, align='L', fill=False)
                    self.set_xy(x + w_course, current_y)
                    self.multi_cell_fixed_height(w_title, row_height, title_text, border=1, align='L', fill=False)
                    self.set_xy(x + w_course + w_title, current_y)
                    self.multi_cell_fixed_height(w_cr, row_height, credits_text, border=1, align='C', fill=False)
                    self.set_text_color(0, 0, 0)
                    self.set_xy(x, current_y + row_height)
                else:
                    course = entry
                    course_label = course.get("label", "No Label") or "No Label"
                    row_color = label_colors.get(course_label, (0, 0, 0))
                    course_code = f"{course.get('subject', '')} {course.get('number', '')}".strip()
                    title = course.get("name", "")
                    cr = course.get("credits", "")
                    code_lines = self.wrap_text(course_code, max_w_course)
                    title_lines = self.wrap_text(title, max_w_title)
                    total_lines = max(len(code_lines), len(title_lines), 1)
                    line_h = 4
                    row_height = max(10, total_lines * line_h + 4)
                    current_y = self.get_y()
                    self.set_xy(x, current_y)
                    self.set_text_color(*row_color)
                    self.multi_cell_fixed_height(w_course, row_height, course_code, border=1, align='L', fill=False)
                    self.set_xy(x + w_course, current_y)
                    self.multi_cell_fixed_height(w_title, row_height, title, border=1, align='L', fill=False)
                    self.set_xy(x + w_course + w_title, current_y)
                    self.multi_cell_fixed_height(w_cr, row_height, str(cr), border=1, align='C', fill=False)
                    self.set_text_color(0, 0, 0)
                    self.set_xy(x, current_y + row_height)
            return self.get_y()

        def estimate_block_height(self, courses):
            total = 8 + 8
            w_course, w_title, pad, line_h = 20, 55, 2, 4
            max_w_course, max_w_title = w_course - pad, w_title - pad
            for entry in courses:
                if isinstance(entry, dict) and entry.get("type") == "group":
                    options = entry.get("courses", [])
                    option_titles = []
                    for opt in options:
                        titles = [c.get("name", "") for c in opt]
                        option_titles.append(" + ".join(titles))
                    title_text = "  OR  ".join(option_titles)
                    title_lines = self.wrap_text(title_text, max_w_title)
                    total_lines = max(1, len(title_lines))
                    row_height = max(10, total_lines * line_h + 4)
                    total += row_height
                else:
                    course = entry
                    course_code = f"{course.get('subject', '')} {course.get('number', '')}".strip()
                    title = course.get("name", "")
                    code_lines = self.wrap_text(course_code, max_w_course)
                    title_lines = self.wrap_text(title, max_w_title)
                    total_lines = max(len(code_lines), len(title_lines), 1)
                    row_height = max(10, total_lines * line_h + 4)
                    total += row_height
            total += 2
            return total

    pdf = PDF()
    i = 0
    while i < len(semesters):
        sem1 = semesters[i]
        courses1 = sem1.get("courses", [])
        credits1 = compute_semester_credits(courses1)
        term1_key = f"{sem1['level']} - {sem1['term']} ({credits1} cr)"
        color1 = level_colors.get(sem1.get("level", ""), (255, 255, 255))

        if sem1["term"].lower() == "summer":
            full_text = f"{term1_key}: " + ", ".join(
                [f"{c.get('label','Group')} ({c.get('credits','')})" if isinstance(c, dict) and c.get("type") == "group" 
                 else f"({c.get('subject','')} {c.get('number','')}) ({c.get('credits','')} credits)" for c in courses1]
            )
            lines = pdf.wrap_text(full_text, pdf.page_w)
            needed_h = max(8, len(lines) * 8 + 2)
            available_h = pdf.h - pdf.b_margin - pdf.y_start
            if needed_h > available_h:
                pdf.add_page()
                pdf.y_start = getattr(pdf, "y_start", pdf.get_y())
            pdf.set_xy(pdf.left_x, pdf.y_start - 4)
            pdf.set_font("Times", "B", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(pdf.page_w, 8, full_text, align='C')
            pdf.y_start = pdf.get_y() + 6
            i += 1
            continue

        h1 = pdf.estimate_block_height(courses1)
        if i + 1 < len(semesters) and semesters[i + 1]["term"].lower() != "summer":
            sem2 = semesters[i + 1]
            courses2 = sem2.get("courses", [])
            credits2 = compute_semester_credits(courses2)
            term2_key = f"{sem2['level']} - {sem2['term']} ({credits2} cr)"
            color2 = level_colors.get(sem2.get("level", ""), (255, 255, 255))
            h2 = pdf.estimate_block_height(courses2)
            required_h = max(h1, h2)
            available_h = pdf.h - pdf.b_margin - pdf.y_start
            if required_h > available_h:
                pdf.add_page()
                pdf.y_start = getattr(pdf, "y_start", pdf.get_y())
            y_start = pdf.y_start
            y1_end = pdf.semester_block(pdf.left_x, y_start, term1_key, courses1, color1, credits1)
            y2_end = pdf.semester_block(pdf.right_x, y_start, term2_key, courses2, color2, credits2)
            pdf.y_start = max(y1_end, y2_end) + 10
            i += 2
        else:
            available_h = pdf.h - pdf.b_margin - pdf.y_start
            if h1 > available_h:
                pdf.add_page()
                pdf.y_start = getattr(pdf, "y_start", pdf.get_y())
            y1_end = pdf.semester_block(pdf.left_x, pdf.y_start, term1_key, courses1, color1, credits1)
            pdf.y_start = y1_end + 10
            i += 1

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer = BytesIO(pdf_bytes)
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="academic_plan.pdf",
        mimetype="application/pdf"
    )
