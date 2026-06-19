"""Export the FastAPI OpenAPI spec to openapi.json.

Usage (from repo root, with venv active):
    python scripts/export_openapi.py

Output: openapi.json at repo root — hand to Aswin for UI development.
"""
import json
import os
import sys

# Minimal env so FastAPI app imports without crashing
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "export-script-placeholder")
os.environ.setdefault("GOOGLE_CLIENT_ID", "placeholder")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "placeholder")
os.environ.setdefault("S3_BUCKET_NAME", "placeholder")
os.environ.setdefault("SES_FROM_EMAIL", "placeholder@example.com")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: E402

spec = app.openapi()
out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "openapi.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)

print(f"OpenAPI spec written to {out_path}  ({len(spec['paths'])} paths)")
