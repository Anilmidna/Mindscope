"""SVG chart generators for MindScope PDF reports.

Pure Python — no matplotlib, no JS. All charts generated as SVG strings.
Each function accepts score dicts matching the output of the scoring engines
and returns a complete SVG string ready to embed in HTML/PDF.
"""
import math


# ── Shared helpers ────────────────────────────────────────────────────────────

def _color_by_percentile(pct: float) -> str:
    """Return hex color based on percentile band."""
    if pct >= 70:
        return "#63B3ED"   # blue — high
    if pct >= 30:
        return "#68D391"   # green — mid
    return "#FC8181"       # red — low


# ── RIASEC Hexagonal Radar Chart ─────────────────────────────────────────────

def generate_riasec_radar(scores: dict) -> str:
    """
    Hexagonal radar chart for RIASEC scores (0–100 each).

    scores: {"R": 72.5, "I": 88.0, "A": 45.0, "S": 71.0, "E": 55.0, "C": 38.0}
    Returns a 400×400 SVG string.
    """
    cx, cy = 200, 200
    max_r = 150  # radius for score=100
    axes = ["R", "I", "A", "S", "E", "C"]
    labels = {
        "R": "Realistic",
        "I": "Investigative",
        "A": "Artistic",
        "S": "Social",
        "E": "Enterprising",
        "C": "Conventional",
    }
    n = len(axes)

    def polar(angle_deg: float, radius: float):
        rad = math.radians(angle_deg - 90)  # start at top
        return cx + radius * math.cos(rad), cy + radius * math.sin(rad)

    def points_str(pts):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    angles = [i * 360 / n for i in range(n)]

    lines = []
    lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">')
    lines.append('  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>')

    # Grid rings at 25%, 50%, 75%, 100%
    for pct in [25, 50, 75, 100]:
        r = max_r * pct / 100
        ring_pts = [polar(a, r) for a in angles]
        lines.append(f'  <polygon points="{points_str(ring_pts)}" fill="none" stroke="#E2E8F0" stroke-width="1"/>')

    # Axis lines from center to edge
    for a in angles:
        ex, ey = polar(a, max_r)
        lines.append(f'  <line x1="{cx}" y1="{cy}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#CBD5E0" stroke-width="1"/>')

    # User score polygon
    user_pts = []
    for i, axis in enumerate(axes):
        score = scores.get(axis, 0)
        r = max_r * score / 100
        user_pts.append(polar(angles[i], r))
    lines.append(f'  <polygon points="{points_str(user_pts)}" fill="rgba(99,102,241,0.25)" stroke="#6366F1" stroke-width="2.5"/>')

    # Dots at each vertex
    for pt in user_pts:
        lines.append(f'  <circle cx="{pt[0]:.1f}" cy="{pt[1]:.1f}" r="4" fill="#6366F1"/>')

    # Axis labels + score values
    label_offset = max_r + 24
    for i, axis in enumerate(axes):
        lx, ly = polar(angles[i], label_offset)
        score_val = scores.get(axis, 0)
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        lines.append(f'  <text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" font-size="11" fill="#4A5568" font-weight="600">{labels[axis]}</text>')
        lines.append(f'  <text x="{lx:.1f}" y="{ly + 14:.1f}" text-anchor="{anchor}" dominant-baseline="middle" font-size="10" fill="#6366F1">{score_val:.0f}</text>')

    lines.append('</svg>')
    return "\n".join(lines)


# ── OCEAN Horizontal Bar Chart ────────────────────────────────────────────────

def generate_ocean_bars(scores: dict, percentiles: dict) -> str:
    """
    Horizontal percentile bar chart for Big Five / OCEAN.

    scores:      {"O": 34, "C": 28, "E": 22, "A": 38, "N": 19}
    percentiles: {"O": 82.5, "C": 45.0, "E": 33.2, "A": 91.1, "N": 28.4}
    Returns a 480×340 SVG string.
    """
    traits = ["O", "C", "E", "A", "N"]
    labels = {
        "O": "Openness",
        "C": "Conscientiousness",
        "E": "Extraversion",
        "A": "Agreeableness",
        "N": "Neuroticism",
    }

    svg_w, svg_h = 480, 340
    label_w = 142
    bar_area_w = 288
    bar_h = 26
    row_h = 52
    top_pad = 20
    axis_y = svg_h - 28

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">')
    lines.append('  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>')
    lines.append(f'  <rect width="{svg_w}" height="{svg_h}" fill="#FAFAFA" rx="4"/>')

    # Vertical grid lines at 0, 25, 50, 75, 100
    for tick in [0, 25, 50, 75, 100]:
        tx = label_w + int(bar_area_w * tick / 100)
        lines.append(f'  <line x1="{tx}" y1="{top_pad}" x2="{tx}" y2="{axis_y}" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="3,3"/>')
        lines.append(f'  <text x="{tx}" y="{axis_y + 14}" text-anchor="middle" font-size="9" fill="#A0AEC0">{tick}</text>')

    for i, trait in enumerate(traits):
        pct = percentiles.get(trait, 50.0)
        raw = scores.get(trait, 0)
        bar_w = int(bar_area_w * pct / 100)
        y = top_pad + i * row_h
        color = _color_by_percentile(pct)

        # Trait label
        lines.append(f'  <text x="{label_w - 8}" y="{y + bar_h / 2 + 1:.0f}" text-anchor="end" dominant-baseline="middle" font-size="11" fill="#2D3748" font-weight="600">{labels[trait]}</text>')

        # Background track
        lines.append(f'  <rect x="{label_w}" y="{y}" width="{bar_area_w}" height="{bar_h}" fill="#EDF2F7" rx="3"/>')

        # Filled bar
        if bar_w > 0:
            lines.append(f'  <rect x="{label_w}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{color}" rx="3"/>')

        # Percentile text
        label_x = label_w + bar_w + 6
        lines.append(f'  <text x="{label_x}" y="{y + bar_h / 2 + 1:.0f}" dominant-baseline="middle" font-size="10" fill="#4A5568" font-weight="600">{pct:.0f}th</text>')

        # Raw score (small)
        lines.append(f'  <text x="{label_w + bar_area_w + 42}" y="{y + bar_h / 2 + 1:.0f}" dominant-baseline="middle" font-size="9" fill="#A0AEC0">({raw:.0f})</text>')

    lines.append(f'  <text x="{label_w + bar_area_w // 2}" y="{svg_h - 4}" text-anchor="middle" font-size="9" fill="#A0AEC0">Percentile</text>')
    lines.append('</svg>')
    return "\n".join(lines)


# ── Aptitude Horizontal Bar Chart ─────────────────────────────────────────────

def generate_aptitude_bars(scores: dict, percentiles: dict) -> str:
    """
    Horizontal percentile bar chart for 4 aptitude domains.

    scores:      {"logical": 11, "numerical": 9, "verbal": 12, "spatial": 8}
    percentiles: {"logical": 84.1, "numerical": 74.2, "verbal": 91.0, "spatial": 62.3}
    Returns a 480×270 SVG string.
    """
    domains = ["logical", "numerical", "verbal", "spatial"]
    labels = {
        "logical":   "Logical Reasoning",
        "numerical": "Numerical Ability",
        "verbal":    "Verbal Ability",
        "spatial":   "Spatial Reasoning",
    }

    svg_w, svg_h = 480, 270
    label_w = 152
    bar_area_w = 278
    bar_h = 26
    row_h = 52
    top_pad = 20
    axis_y = svg_h - 28

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">')
    lines.append('  <style>text { font-family: Arial, Helvetica, sans-serif; }</style>')
    lines.append(f'  <rect width="{svg_w}" height="{svg_h}" fill="#FAFAFA" rx="4"/>')

    for tick in [0, 25, 50, 75, 100]:
        tx = label_w + int(bar_area_w * tick / 100)
        lines.append(f'  <line x1="{tx}" y1="{top_pad}" x2="{tx}" y2="{axis_y}" stroke="#E2E8F0" stroke-width="1" stroke-dasharray="3,3"/>')
        lines.append(f'  <text x="{tx}" y="{axis_y + 14}" text-anchor="middle" font-size="9" fill="#A0AEC0">{tick}</text>')

    for i, domain in enumerate(domains):
        pct = percentiles.get(domain, 50.0)
        raw = scores.get(domain, 0)
        bar_w = int(bar_area_w * pct / 100)
        y = top_pad + i * row_h
        color = _color_by_percentile(pct)

        lines.append(f'  <text x="{label_w - 8}" y="{y + bar_h / 2 + 1:.0f}" text-anchor="end" dominant-baseline="middle" font-size="11" fill="#2D3748" font-weight="600">{labels[domain]}</text>')
        lines.append(f'  <rect x="{label_w}" y="{y}" width="{bar_area_w}" height="{bar_h}" fill="#EDF2F7" rx="3"/>')
        if bar_w > 0:
            lines.append(f'  <rect x="{label_w}" y="{y}" width="{bar_w}" height="{bar_h}" fill="{color}" rx="3"/>')

        label_x = label_w + bar_w + 6
        lines.append(f'  <text x="{label_x}" y="{y + bar_h / 2 + 1:.0f}" dominant-baseline="middle" font-size="10" fill="#4A5568" font-weight="600">{pct:.0f}th</text>')
        lines.append(f'  <text x="{label_w + bar_area_w + 42}" y="{y + bar_h / 2 + 1:.0f}" dominant-baseline="middle" font-size="9" fill="#A0AEC0">{raw:.0f}/15</text>')

    lines.append(f'  <text x="{label_w + bar_area_w // 2}" y="{svg_h - 4}" text-anchor="middle" font-size="9" fill="#A0AEC0">Percentile</text>')
    lines.append('</svg>')
    return "\n".join(lines)
