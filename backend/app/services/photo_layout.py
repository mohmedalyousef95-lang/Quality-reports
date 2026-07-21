"""Dynamic photo placement geometry for report slides.

Uniform-grid layout with cover-crop: every photo occupies an identical cell,
filling the content area completely with equal gaps — sizes are consistent
and margins symmetric, like an executive report. Each image is centre-cropped
(within a limit) to fill its cell without distortion; when the required crop
would be excessive the image falls back to aspect-fit inside its cell.

All units are EMU (English Metric Units, 914400 per inch) to match python-pptx.
"""

EMU_PER_INCH = 914400

# candidate grids (columns × rows) per photo count; best-scoring one is used
GRID_CANDIDATES = {
    1: [(1, 1)],
    2: [(2, 1), (1, 2)],
    3: [(3, 1), (2, 2)],
    4: [(2, 2), (3, 2)],
    5: [(3, 2), (2, 3)],
    # Always exactly 2 rows (3 columns) for 6 photos — large, clear tiles
    # that fill the slide, per explicit request.
    6: [(3, 2)],
    7: [(4, 2), (3, 3)],
    8: [(4, 2)],
    9: [(3, 3)],
    10: [(5, 2), (4, 3)],
}

# Never crop away more than this fraction of a photo's width/height.
MAX_CROP = 0.5


def compute_layout(n, area, aspects, captions, gap, caption_h):
    """Pick the grid whose cells need the least cropping/letterboxing overall."""
    n = max(1, min(10, len(aspects) if aspects else n))
    aspects = [(a if a else 1.0) for a in (aspects or [1.0] * n)]
    captions = list(captions or [False] * n)

    l0, t0, w0, h0 = area
    any_cap = any(captions[:n])

    best, best_cost = None, None
    for cols, rows in GRID_CANDIDATES[n]:
        cell_w = (w0 - (cols - 1) * gap) / cols
        cell_h = (h0 - (rows - 1) * gap) / rows
        img_h = cell_h - (caption_h if any_cap else 0)
        if img_h <= 0 or cell_w <= 0:
            continue
        box = cell_w / img_h
        cost = 0.0
        for a in aspects[:n]:
            frac = 1.0 - (box / a if a >= box else a / box)  # crop needed to cover
            if frac <= MAX_CROP:
                cost += frac  # mild, allowed crop
            else:
                cost += frac + 0.25  # letterbox waste + penalty for not filling
        if best_cost is None or cost < best_cost:
            best_cost, best = cost, (cols, rows)

    return _grid_layout(n, area, aspects, captions, gap, caption_h, best)


def _grid_layout(n, area, aspects, captions, gap, caption_h, grid):
    """Return a list of {'img': rect, 'crop': (l,r,t,b) | None, 'caption': rect | None}.

    area: (left, top, width, height) content rectangle in EMU
    aspects: list of width/height ratios per image
    captions: list of bool — whether each image has a caption
    gap: spacing between cells in EMU
    caption_h: caption bar height in EMU

    Caption rects share the cell width, so caption boxes are identical across
    the slide. Cells without a caption simply leave that strip empty, keeping
    every image the same size and the grid perfectly aligned.
    """
    l0, t0, w0, h0 = area
    cols, rows = grid
    any_cap = any(captions[:n])

    cell_w = (w0 - (cols - 1) * gap) / cols
    cell_h = (h0 - (rows - 1) * gap) / rows
    img_h = cell_h - (caption_h if any_cap else 0)
    box_aspect = cell_w / img_h if img_h else 1.0

    rects = []
    idx = 0
    for r in range(rows):
        remaining = n - idx
        if remaining <= 0:
            break
        items = min(cols, remaining)
        row_w = items * cell_w + (items - 1) * gap
        x0 = l0 + (w0 - row_w) / 2  # centre a partial last row
        y = t0 + r * (cell_h + gap)
        for c in range(items):
            x = x0 + c * (cell_w + gap)
            a = aspects[idx]

            crop = None
            img_rect = (int(x), int(y), int(cell_w), int(img_h))
            if a >= box_aspect:
                frac = 1.0 - (box_aspect / a)
                if frac <= MAX_CROP:
                    side = frac / 2
                    crop = (side, side, 0.0, 0.0)  # crop left/right
            else:
                frac = 1.0 - (a / box_aspect)
                if frac <= MAX_CROP:
                    side = frac / 2
                    crop = (0.0, 0.0, side, side)  # crop top/bottom

            fitted = False
            if crop is None and abs(a - box_aspect) > 1e-6:
                # Fit inside the cell (no crop), centred — used when covering
                # would cut away too much of the photo.
                fitted = True
                if a > box_aspect:
                    fw, fh = cell_w, cell_w / a
                else:
                    fh, fw = img_h, img_h * a
                img_rect = (
                    int(x + (cell_w - fw) / 2),
                    int(y + (img_h - fh) / 2),
                    int(fw),
                    int(fh),
                )
            elif crop is None:
                crop = (0.0, 0.0, 0.0, 0.0)

            cap_rect = None
            if idx < len(captions) and captions[idx]:
                if fitted:
                    # Attach the caption directly under the fitted image, at
                    # the image's own width, so it doesn't float detached.
                    fx, fy, fw2, fh2 = img_rect
                    cap_rect = (fx, fy + fh2, fw2, int(caption_h))
                else:
                    cap_rect = (int(x), int(y + img_h), int(cell_w), int(caption_h))

            rects.append({"img": img_rect, "crop": crop, "caption": cap_rect})
            idx += 1
    return rects
