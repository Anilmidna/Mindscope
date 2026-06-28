"""
Report generation pipeline.

Flow:
  responses in DB
  → score (RIASEC + OCEAN + Aptitude)
  → build profile
  → Bedrock (llm_service) → report JSON
  → PDF (WeasyPrint via pdf_service)
  → S3 upload
  → SES email with pre-signed download link
"""
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.llm import llm_service, BEDROCK_MODELS, PROMPT_TEMPLATE_VERSION
from app.services.email_service import send_report_ready_email
from app.services.pdf_service import generate_pdf, render_html, scores_from_db_row
from app.services.report_validator import validate_report

logger = logging.getLogger(__name__)
from app.models.bias_flag import BiasFlag
from app.models.intake import IntakeForm
from app.models.norm_group import NormGroup
from app.models.report import Report
from app.models.response import Response
from app.models.score import Score
from app.models.session import AssessmentSession
from scoring.aptitude import score as aptitude_score
from scoring.ocean import score as ocean_score
from scoring.profile_builder import build_profile
from scoring.riasec import score as riasec_score


def _load_norms(db: Session, context: str) -> dict:
    """Load score_stats from norm_groups table for a given context. Returns {} if not found."""
    row = db.query(NormGroup).filter(NormGroup.context == context).first()
    return row.score_stats if row and row.score_stats else {}


def _get_responses_by_domain(db: Session, session_id) -> dict:
    rows = db.query(Response).filter(Response.session_id == session_id).all()
    by_domain: dict = {}
    for r in rows:
        by_domain.setdefault(r.domain, []).append({
            "item_id": r.item_id,
            "answer": r.answer,
            "response_time_ms": r.response_time_ms,
        })
    return by_domain


def _flag_response_time_outliers(responses: list[dict]) -> bool:
    """Flag if >20% of responses were answered in under 2 seconds."""
    timed = [r for r in responses if r.get("response_time_ms") is not None]
    if not timed:
        return False
    fast = [r for r in timed if r["response_time_ms"] < 2000]
    return len(fast) / len(timed) > 0.20


def _upload_pdf_to_s3(pdf_bytes: bytes, user_id, session_id) -> Optional[str]:
    """Upload PDF to S3, return the S3 key. Returns None and logs on failure."""
    key = f"reports/{user_id}/{session_id}.pdf"
    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        logger.info("PDF uploaded to s3://%s/%s", settings.S3_BUCKET_NAME, key)
        return key
    except ClientError as e:
        logger.warning("S3 upload failed for %s: %s", key, e.response["Error"]["Message"])
        return None


def _make_presigned_url(s3_key: str, expires: int = 3600) -> Optional[str]:
    """Generate a pre-signed GET URL for an S3 object. Returns None on failure."""
    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires,
        )
    except ClientError as e:
        logger.warning("Pre-signed URL failed for %s: %s", s3_key, e.response["Error"]["Message"])
        return None


def run_scoring_pipeline(
    db: Session,
    session: AssessmentSession,
    model_override: Optional[str] = None,
) -> Report:
    """
    Full pipeline:
    1. Load responses from DB
    2. Score RIASEC + OCEAN + Aptitude
    3. Persist scores + bias flags
    4. Build structured profile
    5. Call Bedrock → report JSON
    6. Persist report record
    7. Generate PDF (WeasyPrint)
    8. Upload PDF to S3
    9. Send SES email with pre-signed download link
    Returns the Report ORM object.
    """
    # ── Mark report as generating ─────────────────────────────────────────
    report = db.query(Report).filter(Report.session_id == session.id).first()
    if not report:
        report = Report(session_id=session.id, status="generating")
        db.add(report)
    else:
        report.status = "generating"
    db.commit()
    logger.info("Scoring pipeline started", extra={"session_id": str(session.id),
                                                    "user_id": str(session.user_id)})

    try:
        # ── 1. Load responses ──────────────────────────────────────────────
        by_domain = _get_responses_by_domain(db, session.id)

        riasec_responses = by_domain.get("RIASEC", [])
        ocean_responses = by_domain.get("OCEAN", [])
        aptitude_responses = {
            "Logical":   by_domain.get("Logical", []),
            "Numerical": by_domain.get("Numerical", []),
            "Verbal":    by_domain.get("Verbal", []),
            "Spatial":   by_domain.get("Spatial", []),
        }

        # ── 2. Score (with DB-sourced norms, fallback to hardcoded if table empty) ──
        riasec_norms = _load_norms(db, "riasec-general")
        ocean_norms = _load_norms(db, "ocean-general")
        aptitude_norms = _load_norms(db, "aptitude-india-graduate")

        riasec_result = riasec_score(riasec_responses, norms=riasec_norms or None)
        ocean_result = ocean_score(ocean_responses, norms=ocean_norms or None)
        aptitude_result = aptitude_score(aptitude_responses, norms=aptitude_norms or None)
        aptitude = aptitude_result.as_scores_dict()

        # ── 3. Bias flags ──────────────────────────────────────────────────
        all_responses = [r for domain_list in by_domain.values() for r in domain_list]
        time_outlier = _flag_response_time_outliers(all_responses)

        bias = db.query(BiasFlag).filter(BiasFlag.session_id == session.id).first()
        if not bias:
            bias = BiasFlag(session_id=session.id)
            db.add(bias)
        bias.social_desirability_score = ocean_result.social_desirability_score
        bias.response_time_outlier_flag = time_outlier
        bias.flagged_for_review = time_outlier
        db.commit()

        # ── 4. Persist scores ──────────────────────────────────────────────
        percentiles = {
            "riasec": riasec_result.percentiles,
            "ocean": ocean_result.percentiles,
            "aptitude": aptitude_result.as_percentiles_dict(),
        }

        score_row = db.query(Score).filter(Score.session_id == session.id).first()
        if not score_row:
            score_row = Score(session_id=session.id)
            db.add(score_row)

        score_row.riasec_r = riasec_result.normalized["R"]
        score_row.riasec_i = riasec_result.normalized["I"]
        score_row.riasec_a = riasec_result.normalized["A"]
        score_row.riasec_s = riasec_result.normalized["S"]
        score_row.riasec_e = riasec_result.normalized["E"]
        score_row.riasec_c = riasec_result.normalized["C"]
        score_row.ocean_o = ocean_result.raw_scores["O"]
        score_row.ocean_c = ocean_result.raw_scores["C"]
        score_row.ocean_e = ocean_result.raw_scores["E"]
        score_row.ocean_a = ocean_result.raw_scores["A"]
        score_row.ocean_n = ocean_result.raw_scores["N"]
        score_row.apt_logical = aptitude["logical"]
        score_row.apt_numerical = aptitude["numerical"]
        score_row.apt_verbal = aptitude["verbal"]
        score_row.apt_spatial = aptitude["spatial"]
        score_row.percentiles = percentiles
        score_row.scoring_engine_version = "1.0"
        db.commit()

        # ── 5. Build profile object ────────────────────────────────────────
        intake_row = db.query(IntakeForm).filter(IntakeForm.session_id == session.id).first()
        intake_dict = {}
        if intake_row:
            intake_dict = {
                "life_stage": intake_row.life_stage,
                "persona": intake_row.persona,
                "domain": intake_row.domain,
                "specialization": intake_row.specialization,
                "future_goals": intake_row.future_goals,
                "satisfaction": intake_row.satisfaction,
                "challenges": intake_row.challenges,
                "education_level": intake_row.education_level,
                "preferred_work_style": intake_row.preferred_work_style,
            }

        profile = build_profile(
            riasec=riasec_result,
            ocean=ocean_result,
            aptitude=aptitude,
            intake=intake_dict,
            norm_group=session.context_of_origin,
        )

        # ── 6. Call Bedrock ────────────────────────────────────────────────
        llm_json = llm_service.generate_report(
            profile=profile,
            intake=intake_dict,
            model=model_override,
        )

        # ── 6b. Validate output (Layer 3 guardrail) ────────────────────────
        is_valid, violations = validate_report(llm_json)
        if not is_valid:
            logger.warning(
                "Report validation failed — retrying with stricter prompt",
                extra={"session_id": str(session.id), "violations": violations},
            )
            llm_json = llm_service.generate_report(
                profile=profile,
                intake=intake_dict,
                model=model_override,
                strict=True,
            )
            is_valid, violations = validate_report(llm_json)
            if not is_valid:
                logger.error(
                    "Report validation failed after retry — flagging for review",
                    extra={"session_id": str(session.id), "violations": violations},
                )
                report.status = "flagged_for_review"
                db.commit()
                raise ValueError(f"Report flagged for review. Violations: {violations}")

        # ── 7. Persist report JSON ─────────────────────────────────────────
        used_model = model_override or llm_service._defaults["report_generation"]
        report.raw_llm_json = json.dumps(llm_json)
        report.prompt_template_version = PROMPT_TEMPLATE_VERSION
        report.llm_model = BEDROCK_MODELS.get(used_model, used_model)
        report.generated_at = datetime.now(timezone.utc)
        report.status = "ready"
        report.template_name = f"report_{session.context_of_origin.replace('-', '_')}"

        # Update session status
        session.status = "complete"
        session.completed_at = datetime.now(timezone.utc)
        session.persona_tag = intake_dict.get("persona")
        db.commit()
        logger.info("Report generated", extra={"session_id": str(session.id),
                                               "user_id": str(session.user_id),
                                               "model": report.llm_model,
                                               "stage": "report_generation"})

        # ── 8. Generate PDF + upload to S3 (TDD §7.4) ────────────────────────
        user_row = session.user
        user_info = {
            "name": user_row.name or "",
            "email": user_row.email or "",
        }
        chart_scores = scores_from_db_row(score_row)
        expected_s3_key = f"reports/{session.user_id}/{session.id}.pdf"

        s3_key = None
        try:
            lambda_fn = settings.PDF_LAMBDA_FUNCTION_NAME
            if lambda_fn:
                # TDD §7: Lambda renders via Playwright + uploads to S3 itself
                html_str = render_html(
                    report_json=llm_json,
                    scores=chart_scores,
                    user=user_info,
                    session_id=str(session.id),
                    context_of_origin=session.context_of_origin,
                )
                import json as _json
                lambda_client = boto3.client("lambda", region_name=settings.AWS_REGION)
                response = lambda_client.invoke(
                    FunctionName=lambda_fn,
                    InvocationType="RequestResponse",
                    Payload=_json.dumps({
                        "html": html_str,
                        "s3_key": expected_s3_key,
                        "s3_bucket": settings.S3_BUCKET_NAME,
                    }).encode(),
                )
                result = _json.loads(response["Payload"].read())
                if result.get("status") == "success":
                    s3_key = result["s3_key"]
                    logger.info("PDF rendered via Lambda: %s", s3_key)
                else:
                    raise RuntimeError(f"Lambda PDF failed: {result}")
            else:
                # WeasyPrint fallback (dev or Lambda not yet deployed)
                pdf_bytes = generate_pdf(
                    report_json=llm_json,
                    scores=chart_scores,
                    user=user_info,
                    session_id=str(session.id),
                    context_of_origin=session.context_of_origin,
                )
                s3_key = _upload_pdf_to_s3(pdf_bytes, session.user_id, session.id)

            if s3_key:
                report.s3_url = s3_key
                db.commit()
        except Exception as pdf_err:
            # PDF failure is non-fatal — JSON report is still available
            logger.warning("PDF generation failed for session %s: %s", session.id, pdf_err)
            s3_key = None

        # ── 9. Send SES email ──────────────────────────────────────────────
        if s3_key:
            presigned_url = _make_presigned_url(s3_key)
            if presigned_url:
                send_report_ready_email(
                    to_email=user_info["email"],
                    user_name=user_info["name"],
                    download_url=presigned_url,
                )

        db.refresh(report)
        return report

    except Exception as e:
        report.status = "failed"
        db.commit()
        raise e
