"""
Report generation pipeline.

Flow: responses in DB → score → build profile → Bedrock (llm_service) → store report record
PDF generation is Week 2 — this sprint delivers the JSON report and stores it.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.llm import llm_service, BEDROCK_MODELS, PROMPT_TEMPLATE_VERSION
from app.models.bias_flag import BiasFlag
from app.models.intake import IntakeForm
from app.models.report import Report
from app.models.response import Response
from app.models.score import Score
from app.models.session import AssessmentSession
from scoring.aptitude import score as aptitude_score
from scoring.ocean import score as ocean_score
from scoring.profile_builder import build_profile
from scoring.riasec import score as riasec_score


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


def run_scoring_pipeline(
    db: Session,
    session: AssessmentSession,
    model_override: Optional[str] = None,
) -> Report:
    """
    Full pipeline:
    1. Load responses from DB
    2. Score RIASEC + OCEAN
    3. Build structured profile
    4. Call Bedrock via llm_service
    5. Persist Score + BiasFlag + Report records
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

        # ── 2. Score ───────────────────────────────────────────────────────
        riasec_result = riasec_score(riasec_responses)
        ocean_result = ocean_score(ocean_responses)
        aptitude_result = aptitude_score(aptitude_responses)
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
            "riasec": riasec_result.normalized,
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

        # ── 7. Persist report ──────────────────────────────────────────────
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
        db.refresh(report)
        return report

    except Exception as e:
        report.status = "failed"
        db.commit()
        raise e
