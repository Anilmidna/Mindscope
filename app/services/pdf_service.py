"""PDF generation pipeline for MindScope reports.

Flow:
  report_json (from Bedrock) + scores (from Score DB row) + user info
  → SVG charts (charts.py)
  → Jinja2 renders HTML (templates/report_*.html)
  → Playwright Lambda OR WeasyPrint fallback → PDF bytes
  → caller uploads bytes to S3
"""
import base64
import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

from app.services.charts import (
    generate_aptitude_bars,
    generate_ocean_bars,
    generate_riasec_radar,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = _REPO_ROOT / "templates"
STATIC_DIR = _REPO_ROOT / "static"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def generate_pdf(
    report_json: dict,
    scores: dict,
    user: dict,
    session_id: str,
    context_of_origin: Optional[str] = None,
    generated_date: Optional[str] = None,
) -> bytes:
    """
    Generate a PDF report and return raw bytes.

    Args:
        report_json: 5-section dict from Bedrock
                     {snapshot, strengths, friction_points,
                      career_directions[], next_steps[]}
        scores: {
            "riasec":   {"R": 72, "I": 88, ...},
            "ocean":    {"raw": {"O": 34, ...}, "percentiles": {"O": 82.5, ...}},
            "aptitude": {"scores": {"logical": 11, ...}, "percentiles": {"logical": 84.1, ...}}
          }
        user:    {"name": str, "email": str}
        session_id: str UUID
        context_of_origin: session context tag
        generated_date: formatted date string; defaults to today

    Returns:
        PDF as bytes
    """
    if generated_date is None:
        generated_date = date.today().strftime("%B %d, %Y")

    # ── Build chart inputs ────────────────────────────────────────────────────
    riasec_scores = scores.get("riasec", {})

    ocean_data = scores.get("ocean", {})
    # Accept both flat {"O": 34} and nested {"raw": {"O": 34}, "percentiles": {...}}
    ocean_raw = ocean_data.get("raw", ocean_data)
    ocean_pct = ocean_data.get("percentiles", {})

    apt_data = scores.get("aptitude", {})
    apt_scores = apt_data.get("scores", apt_data)
    apt_pct = apt_data.get("percentiles", {})

    riasec_svg  = generate_riasec_radar(riasec_scores)
    ocean_svg   = generate_ocean_bars(ocean_raw, ocean_pct)
    aptitude_svg = generate_aptitude_bars(apt_scores, apt_pct)

    # ── Select template by context ────────────────────────────────────────────
    _B2B_CONTEXTS = {"b2b-partner", "DATE-college", "training-program"}
    if context_of_origin in _B2B_CONTEXTS:
        template_name = "report_b2b.html"
    else:
        template_name = "report_default.html"

    # ── Render template ───────────────────────────────────────────────────────
    template = _jinja_env.get_template(template_name)
    html_str = template.render(
        report=report_json,
        scores=scores,
        user=user,
        charts={
            "riasec_svg":   riasec_svg,
            "ocean_svg":    ocean_svg,
            "aptitude_svg": aptitude_svg,
        },
        session_id=str(session_id),
        generated_date=generated_date,
        partner_name=None,
        partner_color=None,
    )

    # WeasyPrint fallback path — returns raw PDF bytes
    # (used in dev or when PDF_LAMBDA_FUNCTION_NAME is not set)
    from weasyprint import HTML, CSS  # lazy import — GTK not available on Windows dev
    css_path = STATIC_DIR / "report.css"
    extra_css = [CSS(filename=str(css_path))] if css_path.exists() else []

    return HTML(
        string=html_str,
        base_url=str(_REPO_ROOT),
    ).write_pdf(stylesheets=extra_css)


def render_html(
    report_json: dict,
    scores: dict,
    user: dict,
    session_id: str,
    context_of_origin: Optional[str] = None,
    generated_date: Optional[str] = None,
) -> str:
    """
    Render the Jinja2 HTML template and return the HTML string.
    Used by report_service when invoking the Playwright Lambda (TDD §7.4 step 4).
    Lambda receives this HTML, renders via Chromium, uploads PDF to S3 directly.
    """
    if generated_date is None:
        generated_date = __import__("datetime").date.today().strftime("%B %d, %Y")

    riasec_scores = scores.get("riasec", {})
    ocean_data = scores.get("ocean", {})
    ocean_raw = ocean_data.get("raw", ocean_data)
    ocean_pct = ocean_data.get("percentiles", {})
    apt_data = scores.get("aptitude", {})
    apt_scores = apt_data.get("scores", apt_data)
    apt_pct = apt_data.get("percentiles", {})

    riasec_svg   = generate_riasec_radar(riasec_scores)
    ocean_svg    = generate_ocean_bars(ocean_raw, ocean_pct)
    aptitude_svg = generate_aptitude_bars(apt_scores, apt_pct)

    _B2B_CONTEXTS = {"b2b-partner", "DATE-college", "training-program"}
    template_name = "report_b2b.html" if context_of_origin in _B2B_CONTEXTS else "report_default.html"

    template = _jinja_env.get_template(template_name)
    return template.render(
        report=report_json,
        scores=scores,
        user=user,
        charts={"riasec_svg": riasec_svg, "ocean_svg": ocean_svg, "aptitude_svg": aptitude_svg},
        session_id=str(session_id),
        generated_date=generated_date,
        partner_name=None,
        partner_color=None,
    )


def scores_from_db_row(score_row) -> dict:
    """
    Convert a Score ORM row into the nested scores dict expected by generate_pdf().

    score_row attributes: riasec_r/i/a/s/e/c, ocean_o/c/e/a/n,
                          apt_logical/numerical/verbal/spatial, percentiles (JSONB)
    """
    percentiles = score_row.percentiles or {}
    return {
        "riasec": {
            "R": score_row.riasec_r or 0,
            "I": score_row.riasec_i or 0,
            "A": score_row.riasec_a or 0,
            "S": score_row.riasec_s or 0,
            "E": score_row.riasec_e or 0,
            "C": score_row.riasec_c or 0,
        },
        "ocean": {
            "raw": {
                "O": score_row.ocean_o or 0,
                "C": score_row.ocean_c or 0,
                "E": score_row.ocean_e or 0,
                "A": score_row.ocean_a or 0,
                "N": score_row.ocean_n or 0,
            },
            "percentiles": percentiles.get("ocean", {}),
        },
        "aptitude": {
            "scores": {
                "logical":   score_row.apt_logical   or 0,
                "numerical": score_row.apt_numerical  or 0,
                "verbal":    score_row.apt_verbal     or 0,
                "spatial":   score_row.apt_spatial    or 0,
            },
            "percentiles": percentiles.get("aptitude", {}),
        },
    }
