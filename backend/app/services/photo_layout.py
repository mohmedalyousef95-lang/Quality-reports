"""Dynamic photo placement geometry for report slides.

Justified-rows layout (like photo galleries): photos are split into rows,
each row shares one height chosen so the row fills the content width, which
handles mixed portrait/landscape sets without large gaps. The whole block is
then scaled to fit and centred both ways.

All units are EMU (English Metric Units, 914400 per inch) to match python-pptx.
"""

EMU_PER_INCH = 914400

# candidate row splits per photo count; the best-scoring one is used
CANDIDATE_SPLITS = {
    1: [[1]],
    2: [[2], [1, 1]],
    3: [[3], [2, 1]],
    4: [[2, 2], [3, 1]],
    5: [[3, 2], [2, 3]],
    6: [[3, 3], [2, 2, 2]],
}


def compute_layout(n, area, aspects, captions, gap, caption_h):
    """Return a list of {'img': (l,t,w,h), 'caption': (l,t,w,h) | None}.

    Tries several row splits and photo orders (original + aspect-sorted) and
    keeps the arrangement with the largest total image area, so mixed
    portrait/landscape sets don't end up with undersized rows.
    Results are returned in the original photo order.
    """
    n = max(1, min(6, len(aspects) if aspects else n))
    aspects = [(a if a else 1.0) for a in (aspects or [1.0] * n)]
    captions = list(captions or [False] * n)

    orders = [list(range(n))]
    by_aspect = sorted(range(n), key=lambda i: -aspects[i])
    if by_aspect != orders[0]:
        orders.append(by_aspect)
    # Interleave wide/narrow so portraits and landscapes share rows.
    interleaved = []
    lo, hi = 0, n - 1
    while lo <= hi:
        interleaved.append(by_aspect[lo])
        if lo != hi:
            interleaved.append(by_aspect[hi])
        lo += 1
        hi -= 1
    if interleaved not in orders:
        orders.append(interleaved)

    best, best_area = None, -1.0
    for order in orders:
        for split in CANDIDATE_SPLITS[n]:
            placed = _layout_once(order, split, area, aspects, captions, gap, caption_h)
            total = sum(r["img"][2] * r["img"][3] for r in placed if r)
            if total > best_area:
                best_area, best = total, placed
    return best


def _layout_once(order, split, area, aspects, captions, gap, caption_h):
    l0, t0, w0, h0 = area

    # Partition the (possibly re-ordered) images into rows.
    rows = []
    idx = 0
    for k in split:
        rows.append(order[idx:idx + k])
        idx += k

    # Row image-height so the row exactly fills the content width.
    row_heights = []
    row_has_cap = []
    for members in rows:
        k = len(members)
        aspect_sum = sum(aspects[i] if aspects[i] else 1.0 for i in members)
        h = (w0 - (k - 1) * gap) / aspect_sum if aspect_sum else h0
        row_heights.append(h)
        row_has_cap.append(any(captions[i] for i in members if i < len(captions)))

    # Scale down uniformly if the stacked rows would overflow the area height.
    cap_total = sum(caption_h for has in row_has_cap if has)
    gaps_total = (len(rows) - 1) * gap
    img_total = sum(row_heights)
    avail_img = h0 - gaps_total - cap_total
    if img_total > avail_img and img_total > 0:
        scale = avail_img / img_total
        row_heights = [h * scale for h in row_heights]

    block_h = sum(row_heights) + gaps_total + cap_total
    y = t0 + max(0, (h0 - block_h) / 2)  # centre vertically

    rects = [None] * len(order)
    for members, h, has_cap in zip(rows, row_heights, row_has_cap):
        widths = [(aspects[i] if aspects[i] else 1.0) * h for i in members]
        row_w = sum(widths) + (len(members) - 1) * gap
        x = l0 + max(0, (w0 - row_w) / 2)  # centre each row horizontally
        for i, w in zip(members, widths):
            cap = None
            if i < len(captions) and captions[i]:
                cap = (int(x), int(y + h), int(w), int(caption_h))
            rects[i] = {
                "img": (int(x), int(y), int(w), int(h)),
                "caption": cap,
            }
            x += w + gap
        y += h + (caption_h if has_cap else 0) + gap
    return rects
