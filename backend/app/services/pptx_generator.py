import io
from collections import defaultdict
from copy import deepcopy

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn

from ..config import TEMPLATE_PATH
from ..constants import (
    COVER_SLIDE_INDEX,
    PHOTO_SLIDE_INDEX,
    NOTE_SLIDE_INDEX,
    PHOTO_CATEGORIES,
    NOTE_CATEGORIES,
    PHOTO_CATEGORY_LABELS,
    NOTE_CATEGORY_LABELS,
)
from .photo_storage import load_photo_bytes


def generate_report_pptx(school, report, output_path) -> None:
    prs = Presentation(TEMPLATE_PATH)

    _fill_cover(prs, school, report)

    photos_by_category = defaultdict(list)
    for photo in sorted(report.photos, key=lambda p: p.position):
        photos_by_category[photo.category].append(photo)

    for category, slide_idx in PHOTO_SLIDE_INDEX.items():
        _fill_photo_slide(prs.slides[slide_idx], photos_by_category.get(category, []))

    notes_by_category = defaultdict(list)
    for note in sorted(report.notes, key=lambda n: n.position):
        notes_by_category[note.category].append(note)

    for category, slide_idx in NOTE_SLIDE_INDEX.items():
        _fill_notes_slide(prs.slides[slide_idx], notes_by_category.get(category, []))

    # Add the summary slide last, then move it to position 1 (after the cover),
    # so the index-based fills above stay valid.
    _add_summary_slide(prs, photos_by_category, notes_by_category)

    prs.save(output_path)


def _add_summary_slide(prs, photos_by_category, notes_by_category) -> None:
    from pptx.util import Pt, Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    total_photos = sum(len(v) for v in photos_by_category.values())
    total_notes = sum(len(v) for v in notes_by_category.values())
    photo_sections = sum(1 for c in PHOTO_CATEGORIES if photos_by_category.get(c))
    note_sections = sum(1 for c in NOTE_CATEGORIES if notes_by_category.get(c))
    completion = round(
        (photo_sections + note_sections) / (len(PHOTO_CATEGORIES) + len(NOTE_CATEGORIES)) * 100
    )

    # Reuse the "Title Only" layout used by the closing slide for a clean look.
    layout = prs.slides[-1].slide_layout
    slide = prs.slides.add_slide(layout)

    if slide.shapes.title is not None:
        slide.shapes.title.text = "ملخص الزيارة"

    lines = [
        f"نسبة اكتمال التقرير: {completion}%",
        f"إجمالي الصور: {total_photos}    |    إجمالي الملاحظات: {total_notes}",
        "",
        "الصور حسب القسم:",
    ]
    for c in PHOTO_CATEGORIES:
        lines.append(f"• {PHOTO_CATEGORY_LABELS[c]}: {len(photos_by_category.get(c, []))}")
    lines.append("")
    lines.append("الملاحظات حسب القسم:")
    for c in NOTE_CATEGORIES:
        lines.append(f"• {NOTE_CATEGORY_LABELS[c]}: {len(notes_by_category.get(c, []))}")

    box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(5))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.RIGHT
        run = p.add_run()
        run.text = line
        run.font.size = Pt(18)
        run.font.name = "Tajawal"
        run.font.color.rgb = RGBColor(0x16, 0x21, 0x1F)
        if line.endswith(":") or "نسبة اكتمال" in line:
            run.font.bold = True

    # Move the newly-appended slide to index 1 (right after the cover).
    sld_lst = prs.slides._sldIdLst
    ids = list(sld_lst)
    sld_lst.remove(ids[-1])
    sld_lst.insert(1, ids[-1])


def _fill_cover(prs, school, report) -> None:
    slide = prs.slides[COVER_SLIDE_INDEX]
    visit_date_str = report.visit_date.strftime("%Y-%m-%d") if report.visit_date else ""
    values = {
        "اسم الزائر": report.visitor_name or "",
        "اسم المدرسة": school.name or "",
        "تاريخ الزيارة": visit_date_str,
    }
    target_tf = None
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for para in shape.text_frame.paragraphs:
            if not para.runs:
                continue
            first_run = para.runs[0]
            for label, value in values.items():
                if first_run.text.startswith(label):
                    first_run.text = first_run.text.rstrip() + " " + value
                    target_tf = shape.text_frame
                    break

    if target_tf is not None:
        # Auto-fit so the added school-info lines never overflow the box.
        try:
            target_tf.word_wrap = True
            target_tf.auto_size = MSO_AUTO_SIZE.SHRINK_TEXT_ON_OVERFLOW
        except Exception:
            pass
        extra = [
            ("الرقم الوزاري", school.ministry_number),
            ("المنطقة", school.region),
            ("الزون", school.zone),
            ("المهندس المرافق", school.engineer),
            ("المشرف", school.supervisor),
            ("العنوان", school.address),
        ]
        last_p = target_tf.paragraphs[-1]._p
        for label, value in extra:
            if not value:
                continue
            new_p = deepcopy(last_p)
            _set_paragraph_text(new_p, f"{label}: {value}")
            last_p.addnext(new_p)
            last_p = new_p


def _set_paragraph_text(p_elem, text: str) -> None:
    runs = p_elem.findall(qn("a:r"))
    if not runs:
        return
    for r in runs[1:]:
        p_elem.remove(r)
    t = runs[0].find(qn("a:t"))
    if t is None:
        t = runs[0].makeelement(qn("a:t"), {})
        runs[0].append(t)
    t.text = text


def _fill_photo_slide(slide, photos) -> None:
    placeholders = [
        sh
        for sh in slide.placeholders
        if sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE
    ]
    placeholders.sort(key=lambda ph: ph.placeholder_format.idx)

    captioned = []
    for ph, photo in zip(placeholders, photos):
        image_bytes = load_photo_bytes(photo.file_path)
        left, top, width, height = ph.left, ph.top, ph.width, ph.height
        ph.insert_picture(io.BytesIO(image_bytes))
        caption = getattr(photo, "caption", "") or ""
        if caption.strip():
            captioned.append((left, top, width, height, caption.strip()))

    for ph in placeholders[len(photos):]:
        ph._element.getparent().remove(ph._element)

    # Caption bars are added after pictures so they render on top.
    for left, top, width, height, caption in captioned:
        _add_caption_bar(slide, left, top, width, height, caption)


def _add_caption_bar(slide, left, top, width, height, text) -> None:
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    bar_h = Pt(20)
    box = slide.shapes.add_textbox(left, top + height - bar_h, width, bar_h)
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0x0F, 0x76, 0x6E)
    box.line.fill.background()
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.margin_left = Pt(4)
    tf.margin_right = Pt(4)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    run.font.name = "Tajawal"


def _fill_notes_slide(slide, notes) -> None:
    table_shape = next(sh for sh in slide.shapes if sh.has_table)
    table = table_shape.table
    tbl = table._tbl

    n_needed = len(notes)
    n_have = len(tbl.tr_lst) - 1  # exclude header row

    if n_needed > n_have:
        last_tr = tbl.tr_lst[-1]
        for _ in range(n_needed - n_have):
            tbl.append(deepcopy(last_tr))
    elif n_needed < n_have:
        for tr in tbl.tr_lst[1 + n_needed:]:
            tbl.remove(tr)

    for i, note in enumerate(notes):
        row = table.rows[i + 1]
        _set_cell_text(row.cells[0], note.item)
        _set_cell_text(row.cells[1], note.note or "")

    total_height = sum(row.height for row in table.rows)
    table_shape.height = total_height


def _set_cell_text(cell, text: str) -> None:
    tf = cell.text_frame
    p = tf.paragraphs[0]
    p_elem = p._p

    if p.runs:
        run = p.runs[0]
        run.text = text
        for extra in list(p.runs[1:]):
            p_elem.remove(extra._r)
    else:
        end_para_rpr = p_elem.find(qn("a:endParaRPr"))
        run = p.add_run()
        run.text = text
        if end_para_rpr is not None:
            new_rpr = deepcopy(end_para_rpr)
            new_rpr.tag = qn("a:rPr")
            existing_rpr = run._r.find(qn("a:rPr"))
            if existing_rpr is not None:
                run._r.remove(existing_rpr)
            run._r.insert(0, new_rpr)
