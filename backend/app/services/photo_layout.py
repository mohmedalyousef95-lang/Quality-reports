"""Dynamic photo placement geometry for report slides.

Given the slide's content area and the number of photos, compute image
rectangles (and caption rectangles) that maximise size while keeping each
image's aspect ratio, centring the arrangement and avoiding large gaps.

All units are EMU (English Metric Units, 914400 per inch) to match python-pptx.
"""

EMU_PER_INCH = 914400

# columns x rows for a given photo count (1..6)
GRID = {
    1: (1, 1),
    2: (2, 1),
    3: (3, 1),
    4: (2, 2),
    5: (3, 2),
    6: (3, 2),
}


def compute_layout(n, area, aspects, captions, gap, caption_h):
    """Return a list of {'img': (l,t,w,h), 'caption': (l,t,w,h) | None}.

    area: (left, top, width, height) content rectangle in EMU
    aspects: list of width/height ratios per image
    captions: list of bool — whether each image has a caption
    gap: spacing between cells in EMU
    caption_h: caption bar height in EMU
    """
    n = max(1, min(6, n))
    l0, t0, w0, h0 = area
    cols, rows = GRID[n]
    cell_w = (w0 - (cols - 1) * gap) / cols
    cell_h = (h0 - (rows - 1) * gap) / rows

    rects = []
    idx = 0
    for r in range(rows):
        remaining = n - idx
        if remaining <= 0:
            break
        items_in_row = min(cols, remaining)
        row_width = items_in_row * cell_w + (items_in_row - 1) * gap
        row_left = l0 + (w0 - row_width) / 2  # centre the (possibly partial) row
        cell_top = t0 + r * (cell_h + gap)
        for c in range(items_in_row):
            cell_left = row_left + c * (cell_w + gap)
            has_cap = captions[idx] if idx < len(captions) else False
            avail_h = cell_h - (caption_h if has_cap else 0)
            ar = aspects[idx] if idx < len(aspects) and aspects[idx] else 1.0

            box_ar = cell_w / avail_h if avail_h else 1.0
            if ar > box_ar:
                iw = cell_w
                ih = iw / ar
            else:
                ih = avail_h
                iw = ih * ar

            ix = cell_left + (cell_w - iw) / 2
            if has_cap:
                iy = cell_top + (avail_h - ih)  # bottom-align so caption sits under it
                cap = (ix, cell_top + avail_h, iw, caption_h)
            else:
                iy = cell_top + (avail_h - ih) / 2  # centre vertically
                cap = None

            rects.append(
                {"img": (int(ix), int(iy), int(iw), int(ih)),
                 "caption": tuple(int(v) for v in cap) if cap else None}
            )
            idx += 1
    return rects
