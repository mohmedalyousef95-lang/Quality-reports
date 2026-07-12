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

    # One combined notes table (section header rows + item rows) replaces the
    # template's six per-category note slides. The original template table is
    # cloned so the merged table keeps the exact template styling (borders,
    # header fill, Tajawal, RTL alignment).
    src_slide = prs.slides[min(NOTE_SLIDE_INDEX.values())]
    notes_layout = src_slide.slide_layout
    src_table_el = next(sh for sh in src_slide.shapes if sh.has_table)._element
    table_template = deepcopy(src_table_el)
    _add_combined_notes_slides(prs, notes_by_category, notes_layout, table_template)

    for idx in sorted(NOTE_SLIDE_INDEX.values(), reverse=True):
        _delete_slide(prs, idx)

    # Order is now: cover, photos ×4, closing, combined-notes…
    # Move the closing slide back to the end, then insert the school-info
    # slide right after the cover.
    _move_slide(prs, from_index=5, to_index=len(prs.slides) - 1)
    _add_school_info_slide(prs, school, report)

    _add_fade_transitions(prs)

    prs.save(output_path)


def _add_fade_transitions(prs) -> None:
    """Subtle fade between all slides (p:transition/p:fade)."""
    for slide in prs.slides:
        sld = slide._element
        if sld.find(qn("p:transition")) is not None:
            continue
        trans = sld.makeelement(qn("p:transition"), {})
        trans.append(sld.makeelement(qn("p:fade"), {}))
        anchor = sld.find(qn("p:clrMapOvr"))
        if anchor is None:
            anchor = sld.find(qn("p:cSld"))
        anchor.addnext(trans)


def _delete_slide(prs, index) -> None:
    sld_id_lst = prs.slides._sldIdLst
    slides = list(sld_id_lst)
    prs.part.drop_rel(slides[index].rId)
    sld_id_lst.remove(slides[index])


def _move_slide(prs, from_index, to_index) -> None:
    sld_id_lst = prs.slides._sldIdLst
    slides = list(sld_id_lst)
    sld_id_lst.remove(slides[from_index])
    sld_id_lst.insert(to_index, slides[from_index])


def _extract_locality(address) -> str:
    if not address:
        return ""
    text = str(address)
    if "حي" in text:
        tail = text.split("حي", 1)[1].strip(" -‏‬")
        return "حي " + tail.split(" - ")[0].strip()
    return ""


def _add_school_info_slide(prs, school, report) -> None:
    from pptx.util import Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    region = school.region or ""
    locality = _extract_locality(school.address)
    location = " - ".join([x for x in [region, locality] if x]) or region

    rows = [
        ("اسم المدرسة", school.name or ""),
        ("الرقم الوزاري", school.ministry_number or ""),
        ("الموقع", location),
        ("الزون", school.zone or ""),
        ("مهندس الزون", school.engineer or ""),
        ("اسم المشرف", school.supervisor or ""),
    ]
    contractor = (getattr(report, "contractor", "") or "").strip()
    if contractor:
        rows.append(("المقاول المسؤول", contractor))

    layout = prs.slides[-1].slide_layout  # "Title Only" (theme background)
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = "معلومات المدرسة"
        _force_title_font(slide.shapes.title)

    # Centred info card built as a 2-column table.
    n = len(rows)
    tbl_w = Inches(10.5)
    row_h = Inches(0.64)
    tbl_h = row_h * n
    content_top, content_bottom = Inches(1.5), Inches(7.2)
    left = int((prs.slide_width - tbl_w) / 2)
    top = int(content_top + max(0, (content_bottom - content_top - tbl_h)) / 2)
    graphic = slide.shapes.add_table(n, 2, left, top, tbl_w, int(tbl_h))
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
        _style_cell(table.cell(i, 1), label, teal, light, bold=True, size=16, anchor=PP_ALIGN.RIGHT)
        _style_cell(table.cell(i, 0), value, dark, white, bold=False, size=16, anchor=PP_ALIGN.RIGHT)
        table.rows[i].height = int(row_h)

    _move_slide(prs, from_index=len(prs.slides) - 1, to_index=1)


def _force_title_font(title_shape, size=26) -> None:
    """Ensure the slide title uses Tajawal at a uniform size (template
    inherits 24pt; the reviewed spec asks for slightly larger titles)."""
    from pptx.util import Pt
    from pptx.oxml.ns import qn as _qn

    for para in title_shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.name = "Tajawal"
            if size:
                run.font.size = Pt(size)
            rPr = run._r.find(_qn("a:rPr"))
            if rPr is not None:
                cs = rPr.find(_qn("a:cs"))
                if cs is None:
                    cs = rPr.makeelement(_qn("a:cs"), {})
                    rPr.append(cs)
                cs.set("typeface", "Tajawal")


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
        "اسم المدرسة": (school.name or "", True, 32),
        "اسم الزائر": (f"الزائر: {report.visitor_name or ''}", False, 14),
        "تاريخ الزيارة": (f"تاريخ الزيارة: {visit_date_str}", False, 14),
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
            from pptx.enum.text import MSO_ANCHOR

            shape.text_frame.word_wrap = True
            shape.text_frame.auto_size = MSO_AUTO_SIZE.SHRINK_TEXT_ON_OVERFLOW
            # Middle-anchor the block so top/bottom whitespace is balanced.
            shape.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        except Exception:
            pass
        break


def _fill_photo_slide(slide, photos) -> None:
    from PIL import Image
    from pptx.util import Inches
    from .photo_layout import compute_layout

    if slide.shapes.title is not None:
        _force_title_font(slide.shapes.title)

    placeholders = [
        sh
        for sh in slide.placeholders
        if sh.placeholder_format.type == PP_PLACEHOLDER.PICTURE
    ]
    # Remove the fixed placeholders; we place pictures dynamically instead.
    for ph in placeholders:
        ph._element.getparent().remove(ph._element)

    # Content area aligned with the title margins (L=0.92, W=11.5) so every
    # slide shares the same gutters and photos use the full slide width.
    area = (Inches(0.92), Inches(1.3), Inches(11.5), Inches(5.95))

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
    caption_h = Inches(0.38)  # fits a two-line caption box (0.03 + 0.34)
    rects = compute_layout(
        n, area,
        [im["aspect"] for im in images],
        [bool(im["caption"]) for im in images],
        gap, caption_h,
    )

    for im, rect in zip(images, rects):
        ix, iy, iw, ih = rect["img"]
        pic = slide.shapes.add_picture(io.BytesIO(im["data"]), ix, iy, iw, ih)
        if rect["crop"]:
            cl, cr, ct, cb = rect["crop"]
            pic.crop_left = cl
            pic.crop_right = cr
            pic.crop_top = ct
            pic.crop_bottom = cb
        _style_picture(pic)
        if rect["caption"] and im["caption"]:
            strip_y = rect["caption"][1]
            _add_caption(slide, rect["img"], strip_y, im["caption"])


def _style_picture(pic) -> None:
    """Light border + soft drop shadow on photos (executive polish)."""
    from pptx.util import Pt
    from pptx.dml.color import RGBColor

    pic.line.color.rgb = RGBColor(0xD9, 0xD9, 0xD9)
    pic.line.width = Pt(0.75)

    spPr = pic._element.spPr
    if spPr.find(qn("a:effectLst")) is not None:
        return
    effect_lst = spPr.makeelement(qn("a:effectLst"), {})
    shadow = spPr.makeelement(
        qn("a:outerShdw"),
        {"blurRad": "50800", "dist": "25400", "dir": "5400000", "rotWithShape": "0"},
    )
    color = spPr.makeelement(qn("a:srgbClr"), {"val": "000000"})
    alpha = spPr.makeelement(qn("a:alpha"), {"val": "35000"})
    color.append(alpha)
    shadow.append(color)
    effect_lst.append(shadow)
    spPr.append(effect_lst)


def _add_caption(slide, img_rect, strip_y, text) -> None:
    """White caption bar as wide as its photo, directly beneath it.

    The frame adapts to the text so nothing ever spills out: one line at
    7pt when it fits, otherwise it wraps to a second line (taller box),
    and shrinks to 6pt as a last resort. Text is centred both ways,
    Tajawal, theme colour #0099A1 with the thin 0F766E border."""
    from pptx.util import Pt, Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

    ix, iy, iw, ih = img_rect
    inner_pt = iw / 12700 - 8  # usable width in points (minus insets)
    est_pt_per_char = 2.6  # average Arabic glyph width at 7pt

    font_size = 7
    lines = 1
    if len(text) * est_pt_per_char > inner_pt:
        lines = 2
        if len(text) * est_pt_per_char > inner_pt * 2:
            font_size = 6
    box_h = Inches(0.18) if lines == 1 else Inches(0.34)

    box = slide.shapes.add_textbox(int(ix), int(strip_y + Inches(0.03)), int(iw), int(box_h))
    box.fill.solid()
    box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    box.line.color.rgb = RGBColor(0x0F, 0x76, 0x6E)
    box.line.width = Pt(0.75)

    tf = box.text_frame
    tf.word_wrap = True
    # normAutofit: PowerPoint itself shrinks the text further if an extreme
    # caption would still overflow the frame — nothing ever spills out.
    from pptx.enum.text import MSO_AUTO_SIZE as _AS

    tf.auto_size = _AS.TEXT_TO_FIT_SHAPE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_top = Pt(1)
    tf.margin_bottom = Pt(1)
    tf.margin_left = Pt(3)
    tf.margin_right = Pt(3)

    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = False
    run.font.color.rgb = RGBColor(0x00, 0x99, 0xA1)
    run.font.name = "Tajawal"
    rPr = run._r.find(qn("a:rPr"))
    cs = rPr.makeelement(qn("a:cs"), {"typeface": "Tajawal"})
    rPr.append(cs)


def _add_combined_notes_slides(prs, notes_by_category, layout, table_template) -> None:
    """One merged notes table: a header, then per-section rows with their items."""
    from pptx.util import Inches

    rows = []  # ("section", label) | ("item", item, note)
    for category in NOTE_CATEGORIES:
        notes = notes_by_category.get(category)
        if not notes:
            continue
        rows.append(("section", NOTE_CATEGORY_LABELS[category]))
        # Priority order: items carrying an actual observation first,
        # empty/OK items after (stable within each group).
        for note in sorted(notes, key=lambda n: 0 if (n.note or "").strip() else 1):
            rows.append(("item", note.item, note.note or ""))

    if not rows:
        return

    # Chunk across slides by actual row heights (section rows reuse the tall
    # header row of the template) so the table never spills past the slide.
    template_trs = table_template.findall(qn("a:graphic") + "/" + qn("a:graphicData") + "/" + qn("a:tbl") + "/" + qn("a:tr"))
    header_h = int(template_trs[0].get("h"))
    item_h = int(template_trs[1].get("h"))
    budget = int(Inches(5.8)) - header_h  # content area minus the header row

    def row_h(row):
        return header_h if row[0] == "section" else item_h

    # A section header is never left as a slide's last row (it moves to the
    # next slide), and a section whose items continue on a new slide gets its
    # header repeated with "(تابع)".
    chunks = []
    current = []
    used = 0
    active = None  # label of the section whose items are currently flowing
    for row in rows:
        if row[0] == "section":
            active = row[1]
        if current and used + row_h(row) > budget:
            moved = current.pop() if current[-1][0] == "section" else None
            chunks.append(current)
            current = []
            used = 0
            if moved is not None:
                current.append(moved)  # fresh header on the new slide, no تابع
                used += header_h
            elif row[0] == "item" and active:
                current.append(("section", f"{active} (تابع)"))
                used += header_h
        current.append(row)
        used += row_h(row)
    if current:
        chunks.append(current)

    for i, chunk in enumerate(chunks):
        title = "ملاحظات الزيارة" if i == 0 else "ملاحظات الزيارة (تابع)"
        _build_notes_table_slide(prs, layout, title, chunk, table_template)


def _build_notes_table_slide(prs, layout, title, chunk, table_template) -> None:
    """Clone the template's own table (its borders, header fill, Tajawal, RTL)
    and rebuild its rows: header + section rows (merged, header-styled) +
    item rows, then enlarge and centre it in the content area."""
    from pptx.util import Inches

    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = title
        _force_title_font(slide.shapes.title)

    gf_el = deepcopy(table_template)
    slide.shapes._spTree.append(gf_el)
    table_shape = next(sh for sh in slide.shapes if sh.has_table)
    table = table_shape.table
    tbl = table._tbl

    header_tr = tbl.tr_lst[0]
    item_tr_template = deepcopy(tbl.tr_lst[1])  # a formatted content row
    for tr in list(tbl.tr_lst[1:]):
        tbl.remove(tr)

    for row in chunk:
        tbl.append(deepcopy(header_tr) if row[0] == "section" else deepcopy(item_tr_template))

    for i, row in enumerate(chunk, start=1):
        cells = table.rows[i].cells
        if row[0] == "section":
            _set_cell_text(cells[0], row[1])
            _set_cell_text(cells[1], "")
            cells[0].merge(cells[1])
        else:
            _, item, note = row
            _set_cell_text(cells[0], item)
            _set_cell_text(cells[1], note or "—")

    # Enlarge and centre (template look preserved; only geometry changes).
    # 11.5" wide = the same gutters as the slide titles (L=0.92).
    new_w = Inches(11.5)
    old_w = sum(col.width for col in table.columns)
    for col in table.columns:
        col.width = int(col.width * new_w / old_w)
    total_h = sum(r.height for r in table.rows)
    table_shape.width = int(new_w)
    table_shape.height = int(total_h)
    table_shape.left = int((prs.slide_width - new_w) / 2)
    content_top, content_bottom = Inches(1.35), Inches(7.2)
    table_shape.top = int(content_top + max(0, (content_bottom - content_top - total_h)) / 2)


def _set_cell_text(cell, text: str) -> None:
    """Set cell text while preserving the template run formatting (Tajawal, RTL)."""
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
