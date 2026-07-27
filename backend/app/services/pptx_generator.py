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

    # Photos are fetched from R2 (a network round-trip each) — loading them
    # all concurrently up front, instead of one-by-one inside each slide,
    # is the single biggest lever on wall-clock generation time for a
    # report with many photos.
    photo_bytes = _prefetch_photo_bytes(report.photos)

    for category, slide_idx in PHOTO_SLIDE_INDEX.items():
        _fill_photo_slide(prs.slides[slide_idx], photos_by_category.get(category, []), photo_bytes)

    notes_by_category = defaultdict(list)
    for note in sorted(report.notes, key=lambda n: n.position):
        notes_by_category[note.category].append(note)

    # One combined notes table (section header rows + item rows) replaces the
    # template's six per-category note slides. The original template table is
    # cloned so the merged table keeps the exact template styling (borders,
    # header fill, Tajawal, RTL alignment). The layout + a detached copy of
    # the table are captured BEFORE deleting those slides — capturing after
    # would leave nothing to capture, and adding the new slides before
    # deleting the old ones (as this used to do) let python-pptx's
    # slide-partname allocator reuse a number that was still in use by one
    # of the freshly-added slides, writing two "slideN.xml" entries with the
    # same name into the .pptx zip. That's a real corruption bug — some
    # viewers pick one arbitrarily, others refuse to open the file. Deleting
    # first keeps every add_slide() call working from a gap-free numbering.
    src_slide = prs.slides[min(NOTE_SLIDE_INDEX.values())]
    notes_layout = src_slide.slide_layout
    src_table_el = next(sh for sh in src_slide.shapes if sh.has_table)._element
    table_template = deepcopy(src_table_el)
    _expand_notes_table_to_three_cols(table_template)

    for idx in sorted(NOTE_SLIDE_INDEX.values(), reverse=True):
        _delete_slide(prs, idx)

    _add_combined_notes_slides(prs, notes_by_category, notes_layout, table_template)

    # Order is now: cover, photos ×4, closing, combined-notes…
    # Move the closing slide back to the end, then insert the school-info
    # slide right after the cover.
    _move_slide(prs, from_index=5, to_index=len(prs.slides) - 1)
    _add_school_info_slide(prs, school, report)

    _add_fade_transitions(prs)
    _renumber_slide_parts(prs)

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


def _renumber_slide_parts(prs) -> None:
    """Force every slide part to a clean, sequential, guaranteed-unique
    partname (slide1.xml, slide2.xml, ...) matching final slide order.

    python-pptx's own slide-adding allocator (PresentationPart._next_slide_partname)
    just computes "slide%d.xml" % (len(sldIdLst) + 1) — it never checks
    whether that name is actually free. Deleting some of the template's
    slides and later adding new ones (as this generator does) reliably
    makes that formula recompute a number that's still used by an
    untouched slide (the closing slide's partname, e.g., never gets
    renamed by a delete elsewhere) — silently writing two zip entries
    with the same name. That's real corruption: some viewers pick one
    arbitrarily, others refuse to open the file. Only a final renumbering
    pass right before save is fully robust against it.
    """
    from pptx.opc.packuri import PackURI

    for i, sld_id in enumerate(prs.slides._sldIdLst, start=1):
        slide_part = prs.part.related_part(sld_id.rId)
        slide_part.partname = PackURI(f"/ppt/slides/slide{i}.xml")


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

    visit_type = (getattr(report, "visit_type", "") or "").strip()
    if visit_type:
        label = "زيارة تفقدية" if visit_type == "تفقدية" else "زيارة أثناء خطة الاستعداد المدرسي"
        rows.append(("نوع الزيارة", label))

    during_readiness = (getattr(report, "during_readiness_plan", "") or "").strip()
    if during_readiness:
        rows.append(("أثناء خطة الاستعداد المدرسي؟", during_readiness))

    team_count = getattr(report, "team_count", None)
    if team_count is not None:
        rows.append(("عدد الفرق أثناء الزيارة", str(team_count)))

    oversight_present = (getattr(report, "oversight_supervisor_present", "") or "").strip()
    if oversight_present:
        rows.append(("مشرف مكتب العمران متواجد؟", oversight_present))

    team_types = (getattr(report, "team_types", "") or "").strip()
    if team_types:
        rows.append(("نوع الفرق الموجودة", team_types))

    important_notes = (getattr(report, "important_notes", "") or "").strip()

    layout = prs.slides[-1].slide_layout  # "Title Only" (theme background)
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        title_shape = slide.shapes.title
        title_shape.text = "معلومات المدرسة"
        _force_title_font(title_shape)
        # This layout is borrowed from the closing slide, whose title sits
        # mid-page (designed to overlay a full-bleed photo there) — wrong
        # for a normal heading here. Pin it to the exact same top banner
        # geometry every other slide's title uses (839788, 365125,
        # 10515600, 722053 EMU) so margins/alignment stay uniform across
        # the whole deck.
        title_shape.left = 839788
        title_shape.top = 365125
        title_shape.width = 10515600
        title_shape.height = 722053

    # Anchored to the top-right (not centred) so it's always the first thing
    # visible and quick to find while editing. Row height/font are tiered by
    # row count so the whole card — worst case 12 rows plus the 2-row notes
    # section — always stays clear of the slide edges.
    n = len(rows)
    total_rows = n + (2 if important_notes else 0)

    if total_rows <= 7:
        row_h, size, notes_header_h, notes_value_h = Inches(0.60), 14, Inches(0.42), Inches(0.90)
    elif total_rows <= 10:
        row_h, size, notes_header_h, notes_value_h = Inches(0.48), 13, Inches(0.36), Inches(0.70)
    else:
        row_h, size, notes_header_h, notes_value_h = Inches(0.38), 12, Inches(0.32), Inches(0.58)

    tbl_w = Inches(7.3)
    right_margin = Inches(0.92)  # same gutter as every other slide's content area
    top = Inches(1.35)  # clears the (now uniformly-positioned) title above it
    tbl_h = row_h * n + ((notes_header_h + notes_value_h) if important_notes else 0)

    left = int(prs.slide_width - right_margin - tbl_w)
    graphic = slide.shapes.add_table(total_rows, 2, left, int(top), int(tbl_w), int(tbl_h))
    table = graphic.table
    table.first_row = False
    table.horz_banding = False
    table.columns[0].width = int(tbl_w * 0.62)  # value (left)
    table.columns[1].width = int(tbl_w * 0.38)  # label (right)

    # Matches the cover's exact identity (#0099A1, Tajawal, same size as the
    # "اسم الزائر" line) so the info slide reads as a continuation of the
    # cover rather than a new style.
    accent = RGBColor(0x00, 0x99, 0xA1)
    light = RGBColor(0xEC, 0xF3, 0xF2)
    white = RGBColor(0xFF, 0xFF, 0xFF)

    for i, (label, value) in enumerate(rows):
        _style_cell(table.cell(i, 1), label, accent, light, bold=True, size=size, anchor=PP_ALIGN.RIGHT)
        _style_cell(table.cell(i, 0), value, accent, white, bold=False, size=size, anchor=PP_ALIGN.RIGHT)
        table.rows[i].height = int(row_h)

    if important_notes:
        header_cell = table.cell(n, 0)
        header_cell.merge(table.cell(n, 1))
        _style_cell(
            header_cell, "الملاحظات المهمة", accent, light, bold=True, size=size, anchor=PP_ALIGN.CENTER
        )
        table.rows[n].height = int(notes_header_h)

        value_cell = table.cell(n + 1, 0)
        value_cell.merge(table.cell(n + 1, 1))
        _style_cell(
            value_cell, important_notes, accent, white, bold=False, size=max(11, size - 1), anchor=PP_ALIGN.RIGHT
        )
        table.rows[n + 1].height = int(notes_value_h)

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


def _prefetch_photo_bytes(photos) -> dict:
    """Load every photo's bytes from storage (R2) concurrently.

    Each load is a network round-trip; doing them one at a time inside
    slide-building serializes report generation on network latency for
    no reason, since the photos are all independent. Returns a
    {file_path: bytes} map for _fill_photo_slide to use instead of
    hitting storage itself."""
    from concurrent.futures import ThreadPoolExecutor

    paths = list({photo.file_path for photo in photos})
    if not paths:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(paths))) as pool:
        results = pool.map(load_photo_bytes, paths)
    return dict(zip(paths, results))


def _fill_photo_slide(slide, photos, photo_bytes) -> None:
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
        data = photo_bytes[photo.file_path]
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
        caption = (getattr(photo, "caption", "") or "").strip()
        images.append({"data": data, "aspect": (w / h) if h else 1.0, "caption": caption})

    n = len(images)
    gap = Inches(0.12)
    caption_h = Inches(0.32)  # fits a two-line caption box (0.03 + 0.28)
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
    6pt when it fits, otherwise it wraps to a second line (taller box),
    and shrinks to 5pt as a last resort. Text is centred both ways,
    Tajawal, theme colour #0099A1 with the thin 0F766E border. Sized a
    notch smaller than before to leave more of the slide for the photos
    themselves, especially with up to 10 photos on one slide."""
    from pptx.util import Pt, Inches
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

    ix, iy, iw, ih = img_rect
    inner_pt = iw / 12700 - 8  # usable width in points (minus insets)
    est_pt_per_char = 2.25  # average Arabic glyph width at 6pt

    font_size = 6
    lines = 1
    if len(text) * est_pt_per_char > inner_pt:
        lines = 2
        if len(text) * est_pt_per_char > inner_pt * 2:
            font_size = 5
    box_h = Inches(0.15) if lines == 1 else Inches(0.28)

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


def _expand_notes_table_to_three_cols(table_template) -> None:
    """Turn the template's cloned 2-column notes table (item | note) into
    the reviewed three-column layout:

    Row 0 — a single cell merged across all 3 columns: "ملاحظات الزيارة"
            (the table's own title banner).
    Row 1 — 3 separate column-title cells: ملاحظة الزيارة | إجراءات
            المعالجة | حالة المعالجة — same fill/font as row 0.
    Row 2+ — item rows (unchanged: 3 separate cells, no merge).

    The new status column is cloned from the note column so it keeps the
    exact same borders/fill/font as the other two."""
    tbl = table_template.find(qn("a:graphic") + "/" + qn("a:graphicData") + "/" + qn("a:tbl"))
    grid = tbl.find(qn("a:tblGrid"))
    grid_cols = grid.findall(qn("a:gridCol"))
    total_w = int(grid_cols[0].get("w")) + int(grid_cols[1].get("w"))

    new_w0 = int(total_w * 0.37)  # ملاحظة الزيارة
    new_w1 = int(total_w * 0.39)  # إجراءات المعالجة
    new_w2 = total_w - new_w0 - new_w1  # حالة المعالجة
    grid_cols[0].set("w", str(new_w0))
    grid_cols[1].set("w", str(new_w1))
    status_col = deepcopy(grid_cols[1])
    status_col.set("w", str(new_w2))
    grid.append(status_col)

    # Every <a:tr> in this template ends with a trailing <a:extLst> sibling
    # after its 2 original <a:tc> cells. A plain tr.append() would put the
    # new cell AFTER that extLst, which corrupts python-pptx's tc.col_idx
    # (it indexes by position among ALL children, not just <a:tc>) — that
    # silently produced gridSpan="4" merges later instead of "3". Inserting
    # before extLst keeps cells contiguous and column indexing correct.
    trs = tbl.findall(qn("a:tr"))
    for tr in trs:
        tcs = tr.findall(qn("a:tc"))
        new_tc = deepcopy(tcs[1])
        ext_lst = tr.find(qn("a:extLst"))
        if ext_lst is not None:
            ext_lst.addprevious(new_tc)
        else:
            tr.append(new_tc)

    header_tcs = trs[0].findall(qn("a:tc"))
    _set_tc_text(header_tcs[0], "ملاحظة الزيارة")
    _set_tc_text(header_tcs[1], "إجراءات المعالجة")
    _set_tc_text(header_tcs[2], "حالة المعالجة")

    # All 3 column-title cells share one uniform style: turquoise #0099A1
    # fill, bold white Tajawal, centred — the status cell is no longer a
    # special case.
    title_tr = deepcopy(trs[0])
    # <a:tbl>'s schema-fixed child order is tblPr, tblGrid, then tr* — a
    # plain insert(0, ...) put this row before tblGrid, which python-pptx,
    # LibreOffice and plain XML parsers all read past without complaint,
    # but PowerPoint's stricter mobile parser rejects outright ("content
    # this version of Office cannot display"). Inserting right after
    # tblGrid keeps this row first among the <a:tr> siblings while staying
    # schema-valid.
    tbl.insert(list(tbl).index(grid) + 1, title_tr)
    title_tcs = title_tr.findall(qn("a:tc"))
    _set_tc_text(title_tcs[0], "ملاحظات الزيارة")
    _set_tc_text(title_tcs[1], "")
    _set_tc_text(title_tcs[2], "")
    title_tcs[0].set("gridSpan", "3")
    title_tcs[1].set("hMerge", "1")
    title_tcs[2].set("hMerge", "1")

    # Centre the status column's text in the item-row template (row 2) —
    # the header rows are already centred, this only affects data rows.
    item_row = tbl.findall(qn("a:tr"))[2]
    item_status_tc = item_row.findall(qn("a:tc"))[2]
    status_pPr = item_status_tc.find(qn("a:txBody")).find(qn("a:p")).find(qn("a:pPr"))
    if status_pPr is not None:
        status_pPr.set("algn", "ctr")

    # This table gets cloned once per note item/section (potentially dozens
    # of times for a report with many notes), so trimming boilerplate here
    # multiplies into a real file-size/parse-time saving.
    _strip_redundant_border_xml(tbl)

    # Every row/cell/column here traces back to deepcopy()s of the same 2-3
    # template rows, so cloning them dozens of times per report (once per
    # note item) produces many gridCols/rows/cells that all carry the SAME
    # PowerPoint-internal a16:rowId/colId/cellId tracking extensions.
    # PowerPoint mobile apps refuse to open decks containing this — the
    # file reports "content this version of Office cannot display" and
    # won't open, even though the file is otherwise well-formed OOXML.
    # These IDs are optional editing metadata, not required for layout, so
    # stripping them from the template — before it gets cloned further —
    # is both the fix and the simplest one (no clone ever inherits an ID
    # to collide with).
    _strip_a16_tracking_ids(tbl)


def _strip_a16_tracking_ids(tbl) -> None:
    """Remove PowerPoint's internal a16:rowId/colId/cellId tracking
    extensions from every gridCol/tr/tc in the table. rowId, colId and
    cellId each turned out to be wrapped in an <a:ext> with its OWN GUID
    (not a shared one), so this matches by namespace — any <a:ext> whose
    only content is an element in the a16 (2014 main) namespace — rather
    than hardcoding each GUID. Leaves any other extLst content, should
    this template ever gain any, untouched."""
    a16_ns = "http://schemas.microsoft.com/office/drawing/2014/main"
    for parent_tag in ("a:gridCol", "a:tr", "a:tc"):
        for el in tbl.iter(qn(parent_tag)):
            ext_lst = el.find(qn("a:extLst"))
            if ext_lst is None:
                continue
            for ext in list(ext_lst.findall(qn("a:ext"))):
                if any(child.tag.startswith(f"{{{a16_ns}}}") for child in ext):
                    ext_lst.remove(ext)
            if len(ext_lst) == 0:
                el.remove(ext_lst)


def _strip_redundant_border_xml(tbl) -> None:
    """Drop per-border child elements that just restate OOXML defaults
    (solid dash, no arrowheads) — identical rendering, smaller XML."""
    for ln_tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for ln in tbl.iter(qn(ln_tag)):
            for child_tag, default_attrs in (
                ("a:prstDash", {"val": "solid"}),
                ("a:headEnd", {"type": "none"}),
                ("a:tailEnd", {"type": "none"}),
            ):
                child = ln.find(qn(child_tag))
                if child is not None and all(
                    child.get(k) == v for k, v in default_attrs.items()
                ):
                    ln.remove(child)


def _set_tc_text(tc_el, text: str) -> None:
    """Like _set_cell_text, but for a raw <a:tc> element not yet wrapped by
    a python-pptx table (used before the template table is attached to any
    slide)."""
    txBody = tc_el.find(qn("a:txBody"))
    p = txBody.find(qn("a:p"))
    runs = p.findall(qn("a:r"))
    if runs:
        run = runs[0]
        t = run.find(qn("a:t"))
        t.text = text
        for extra in runs[1:]:
            p.remove(extra)
    else:
        end_para_rpr = p.find(qn("a:endParaRPr"))
        run = p.makeelement(qn("a:r"), {})
        if end_para_rpr is not None:
            rpr = deepcopy(end_para_rpr)
            rpr.tag = qn("a:rPr")
            run.append(rpr)
        t = p.makeelement(qn("a:t"), {})
        t.text = text
        run.append(t)
        p.append(run)


def _add_combined_notes_slides(prs, notes_by_category, layout, table_template) -> None:
    """One merged notes table: a header, then per-section rows with their items."""
    from pptx.util import Inches

    rows = []  # ("section", label) | ("item", item, note, status)
    for category in NOTE_CATEGORIES:
        notes = notes_by_category.get(category)
        if not notes:
            continue
        rows.append(("section", NOTE_CATEGORY_LABELS[category]))
        # Priority order: items carrying an actual observation first,
        # empty/OK items after (stable within each group).
        for note in sorted(notes, key=lambda n: 0 if (n.note or "").strip() else 1):
            rows.append(("item", note.item, note.note or "", getattr(note, "status", "") or ""))

    if not rows:
        return

    # Chunk across slides by actual row heights (section rows reuse the tall
    # header row of the template) so the table never spills past the slide.
    # Every slide repeats both fixed rows: the merged title banner (row 0)
    # and the 3-cell column-titles row (row 1).
    template_trs = table_template.findall(qn("a:graphic") + "/" + qn("a:graphicData") + "/" + qn("a:tbl") + "/" + qn("a:tr"))
    title_h = int(template_trs[0].get("h"))
    header_h = int(template_trs[1].get("h"))
    item_h = int(template_trs[2].get("h"))
    budget = int(Inches(5.8)) - title_h - header_h  # content area minus both fixed rows

    def row_h(row):
        return header_h if row[0] == "section" else item_h

    # A section header is never left as a slide's last row (it moves to the
    # next slide), and a section whose items continue on a new slide gets
    # its header repeated as-is — no "(تابع)" suffix anywhere.
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
                current.append(moved)  # fresh header on the new slide
                used += header_h
            elif row[0] == "item" and active:
                current.append(("section", active))
                used += header_h
        current.append(row)
        used += row_h(row)
    if current:
        chunks.append(current)

    for chunk in chunks:
        _build_notes_table_slide(prs, layout, "ملاحظات الزيارة", chunk, table_template)


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

    # tr_lst[0] is the merged title banner, tr_lst[1] the 3-cell column
    # titles — both repeat as-is on every chunk slide. Section rows reuse
    # tr_lst[1]'s style (relabelled + re-merged) for their category banner.
    header_tr = tbl.tr_lst[1]
    item_tr_template = deepcopy(tbl.tr_lst[2])  # a formatted content row
    for tr in list(tbl.tr_lst[2:]):
        tbl.remove(tr)

    for row in chunk:
        tbl.append(deepcopy(header_tr) if row[0] == "section" else deepcopy(item_tr_template))

    for i, row in enumerate(chunk, start=2):
        cells = table.rows[i].cells
        if row[0] == "section":
            _set_cell_text(cells[0], row[1])
            for c_idx in range(1, len(cells)):
                _set_cell_text(cells[c_idx], "")
            cells[0].merge(cells[len(cells) - 1])
        else:
            _, item, note, status = row
            _set_cell_text(cells[0], item)
            _set_cell_text(cells[1], note or "—")
            _set_cell_text(cells[2], status or "—")

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
