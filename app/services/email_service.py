"""SES email delivery for MindScope report notifications."""
import logging

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_report_ready_email(
    to_email: str,
    user_name: str,
    download_url: str,
) -> bool:
    """
    Send report-ready email with a pre-signed download link via SES.
    Returns True on success, False on failure (never raises — caller continues regardless).
    """
    subject = "Your MindScope Assessment Report is Ready"
    display_name = user_name or "there"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #2D3748; max-width: 600px; margin: 0 auto; padding: 32px 16px;">
  <div style="text-align: center; margin-bottom: 32px;">
    <span style="font-size: 22px; font-weight: 700; color: #6366F1; letter-spacing: 3px;">MINDSCOPE</span>
  </div>
  <h2 style="color: #2D3748;">Hi {display_name}, your report is ready!</h2>
  <p style="line-height: 1.7; color: #4A5568;">
    Your MindScope Career &amp; Personality Assessment report has been generated.
    Click the button below to download your personalised PDF report.
  </p>
  <div style="text-align: center; margin: 32px 0;">
    <a href="{download_url}"
       style="background: #6366F1; color: #fff; padding: 14px 32px; border-radius: 8px;
              text-decoration: none; font-weight: 600; font-size: 15px;">
      Download Your Report
    </a>
  </div>
  <p style="font-size: 12px; color: #A0AEC0; line-height: 1.6;">
    This link expires in 1 hour. If it has expired, log back in to MindScope and
    download your report from your dashboard.
  </p>
  <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;">
  <p style="font-size: 11px; color: #CBD5E0; text-align: center;">
    This is a strengths and career-fit tool, not a clinical diagnostic assessment.
  </p>
</body>
</html>
"""

    text_body = (
        f"Hi {display_name},\n\n"
        "Your MindScope Assessment Report is ready.\n\n"
        f"Download it here (link valid for 1 hour):\n{download_url}\n\n"
        "If the link has expired, log back in to MindScope to download from your dashboard.\n\n"
        "— MindScope\n\n"
        "This is a strengths and career-fit tool, not a clinical diagnostic assessment."
    )

    try:
        ses = boto3.client("ses", region_name=settings.AWS_REGION)
        ses.send_email(
            Source=settings.SES_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        logger.info("Report email sent to %s", to_email)
        return True
    except ClientError as e:
        logger.warning("SES email failed for %s: %s", to_email, e.response["Error"]["Message"])
        return False
    except Exception as e:
        logger.warning("SES email unexpected error for %s: %s", to_email, str(e))
        return False
