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

    # Add the school-summary slide last, then move it to position 1 (after the
    # cover), so the index-based fills above stay valid.
    _add_summary_slide(prs, school, report)

    prs.save(output_path)


def _extract_locality(address) -> str:
    if not address:
        return ""
    text = str(address)
    if "حي" in text:
        tail = text.split("حي", 1)[1].strip(" -‏‬")
        return "حي " + tail.split(" - ")[0].strip()
    return ""


def _add_summary_slide(prs, school, report) -> None:
    from pptx.util import Pt, Inches, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

    visit_date_str = report.visit_date.strftime("%Y-%m-%d") if report.visit_date else ""
    region = school.region or ""
    locality = _extract_locality(school.address)
    region_field = " - ".join([x for x in [region, locality] if x]) or region

    rows = [
        ("الرقم الوزاري", school.ministry_number or ""),
        ("اسم المدرسة", school.name or ""),
        ("المنطقة / الحي", region_field),
        ("الزون", school.zone or ""),
        ("مهندس الزون", school.engineer or ""),
        ("المشرف", school.supervisor or ""),
        ("المقاول المسؤول", getattr(report, "contractor", "") or "—"),
        ("تاريخ الزيارة", visit_date_str),
    ]

    layout = prs.slides[-1].slide_layout  # "Title Only" (theme background)
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = "ملخص الزيارة"

    # Centered info card built as a 2-column table.
    n = len(rows)
    tbl_w = Inches(9.5)
    row_h = Inches(0.52)
    tbl_h = row_h * n
    left = int((prs.slide_width - tbl_w) / 2)
    top = int((prs.slide_height - tbl_h) / 2) + Inches(0.4)
    graphic = slide.shapes.add_table(n, 2, left, top, tbl_w, tbl_h)
    table = graphic.table
    table.first_row = False
    table.horz_banding = False
    table.columns[0].width = int(tbl_w * 0.62)  # value (left)
    table.columns[1].width = int(tbl_w * 0.38)  # label (right)

    teal = RGBColor(0x0F, 0x76, 0x6E)
    dark = RGBColor(0x16, 0x21, 0x1F)
    light = RGBColor(0xEC, 0xF3, 0xF2)
    white = RGBColor(0xFF, 0xFF, 0xFF)

    for i, (label, value) in enumerate(rows):
        _style_cell(table.cell(i, 1), label, teal, light, bold=True, size=15, anchor=PP_ALIGN.RIGHT)
        _style_cell(table.cell(i, 0), value, dark, white, bold=False, size=15, anchor=PP_ALIGN.RIGHT)
        table.rows[i].height = row_h

    # Move to index 1 (after the cover).
    sld_lst = prs.slides._sldIdLst
    ids = list(sld_lst)
    sld_lst.remove(ids[-1])
    sld_lst.insert(1, ids[-1])


def _style_cell(cell, text, color, fill, bold, size, anchor) -> None:
    from pptx.util import Pt
    from pptx.enum.text import MSO_ANCHOR

    cell.fill.solid()
    cell.fill.fore_color.rgb = fill
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_top = Pt(2)
    cell.margin_bottom = Pt(2)
    cell.margin_left = Pt(6)
    cell.margin_right = Pt(6)
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = anchor
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = "Tajawal"
    run.font.color.rgb = color


def _fill_cover(prs, school, report) -> None:
    """Cover: school name (bold, large) → visitor (regular) → visit date."""
    from pptx.util import Pt

    slide = prs.slides[COVER_SLIDE_INDEX]
    visit_date_str = report.visit_date.strftime("%Y-%m-%d") if report.visit_date else ""

    # The template's info box has three paragraphs starting with these labels.
    order = ["اسم المدرسة", "اسم الزائر", "تاريخ الزيارة"]
    new_lines = {
        "اسم المدرسة": (school.name or "", True, 28),
        "اسم الزائر": (f"الزائر: {report.visitor_name or ''}", False, 16),
        "تاريخ الزيارة": (f"تاريخ الزيارة: {visit_date_str}", False, 16),
    }

    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        paras = shape.text_frame.paragraphs
        # Identify the info box: first paragraph starts with one of our labels.
        if not paras or not paras[0].runs:
            continue
        first_text = paras[0].runs[0].text
        if not any(first_text.startswith(lbl) for lbl in order):
            continue

        # Relabel each paragraph with its new content/formatting.
        by_label = {}
        for para in paras:
            if not para.runs:
                continue
            label = next((lbl for lbl in order if para.runs[0].text.startswith(lbl)), None)
            if label is None:
                continue
            text, bold, size = new_lines[label]
            run = para.runs[0]
            run.text = text
            for extra in para.runs[1:]:
                extra._r.getparent().remove(extra._r)
            run.font.bold = bold
            run.font.size = Pt(size)
            by_label[label] = para._p

        # Reorder paragraphs to: school → visitor → date.
        txbody = shape.text_frame._txBody
        for label in order:
            p_elem = by_label.get(label)
            if p_elem is not None:
                txbody.remove(p_elem)
                txbody.append(p_elem)
        try:
            shape.text_frame.word_wrap = True
            shape.text_frame.auto_size = MSO_AUTO_SIZE.SHRINK_TEXT_ON_OVERFLOW
        except Exception:
            pass
        break


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
    from PIL import Image
    from pptx.util import Inches
    from .photo_layout import compute_layout

    placeholders = [
        sh
        for sh in slide.placeholders
        if sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE
    ]
    # Content area = bounding box of the template's picture placeholders,
    # so we respect the template's margins/theme.
    if placeholders:
        left = min(ph.left for ph in placeholders)
        top = min(ph.top for ph in placeholders)
        right = max(ph.left + ph.width for ph in placeholders)
        bottom = max(ph.top + ph.height for ph in placeholders)
        area = (left, top, right - left, bottom - top)
    else:
        area = (Inches(1.6), Inches(1.37), Inches(10.17), Inches(5.59))

    # Remove the fixed placeholders; we place pictures dynamically instead.
    for ph in placeholders:
        ph._element.getparent().remove(ph._element)

    if not photos:
        return

    images = []
    for photo in photos:
        data = load_photo_bytes(photo.file_path)
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
        caption = (getattr(photo, "caption", "") or "").strip()
        images.append({"data": data, "aspect": (w / h) if h else 1.0, "caption": caption})

    n = len(images)
    gap = Inches(0.12)
    caption_h = Inches(0.32)
    rects = compute_layout(
        n, area,
        [im["aspect"] for im in images],
        [bool(im["caption"]) for im in images],
        gap, caption_h,
    )

    for im, rect in zip(images, rects):
        ix, iy, iw, ih = rect["img"]
        slide.shapes.add_picture(io.BytesIO(im["data"]), ix, iy, iw, ih)
        if rect["caption"] and im["caption"]:
            _add_caption(slide, rect["caption"], im["caption"])


def _add_caption(slide, box_rect, text) -> None:
    """White caption box with theme-coloured Tajawal text, below the image."""
    from pptx.util import Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

    l, t, w, h = box_rect
    box = slide.shapes.add_textbox(l, t, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    box.line.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
    box.line.width = Pt(0.75)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.margin_left = Pt(3)
    tf.margin_right = Pt(3)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(11)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
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

    # Enlarge and centre the table (horizontally + vertically) in the content
    # area below the title, keeping the template's look.
    from pptx.util import Inches

    slide_w = Inches(13.333)
    content_top = Inches(1.35)
    content_bottom = Inches(6.85)

    new_w = Inches(11.0)
    col_ratio = table.columns[1].width / (table.columns[0].width + table.columns[1].width)
    table.columns[1].width = int(new_w * col_ratio)
    table.columns[0].width = int(new_w - table.columns[1].width)

    total_height = sum(row.height for row in table.rows)
    table_shape.width = int(new_w)
    table_shape.height = int(total_height)
    table_shape.left = int((slide_w - new_w) / 2)
    avail = content_bottom - content_top
    table_shape.top = int(content_top + max(0, (avail - total_height)) / 2)


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
