"""
Playwright Lambda PDF handler (TDD §7.3).

Payload input:  {"html": "<rendered HTML>", "s3_key": "reports/{uid}/{sid}.pdf", "s3_bucket": "mindscope-reports"}
Payload output: {"status": "success", "s3_key": "...", "file_size_bytes": N}

Deployed as AWS Lambda Docker container (ARM64, 1024MB, 30s timeout).
Base image: mcr.microsoft.com/playwright/python:v1.44.0-jammy
"""
import json
import boto3


def handler(event, context):
    html = event.get("html", "")
    s3_key = event.get("s3_key", "")
    bucket = event.get("s3_bucket", "")

    if not html or not s3_key or not bucket:
        return {"status": "error", "error": "Missing required fields: html, s3_key, s3_bucket"}

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.set_content(html, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
        )
        browser.close()

    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=s3_key, Body=pdf_bytes, ContentType="application/pdf")

    return {
        "status": "success",
        "s3_key": s3_key,
        "file_size_bytes": len(pdf_bytes),
    }
