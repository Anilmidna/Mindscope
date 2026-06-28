"""
Create (or update) the MindScope Bedrock Guardrail.

Run once from a machine with AWS credentials that have Bedrock admin access:
    python -m scripts.create_bedrock_guardrail

Prints the guardrailId and guardrailVersion to set in ECS task environment:
    BEDROCK_GUARDRAIL_ID=<id>
    BEDROCK_GUARDRAIL_VERSION=<version>

TDD §8.5 Layer 1 — AWS-native content filtering:
  - Block hate / violence / self-harm at HIGH threshold
  - Denied topics: clinical diagnoses, medication, mental health disorders
  - PII: ANONYMIZE email / phone / SSN
"""
import boto3
import json

GUARDRAIL_NAME = "mindscope-report-guardrail"
REGION = "us-east-1"


def create_or_update():
    client = boto3.client("bedrock", region_name=REGION)

    # Check if guardrail already exists
    existing_id = None
    paginator = client.get_paginator("list_guardrails")
    for page in paginator.paginate():
        for g in page.get("guardrails", []):
            if g["name"] == GUARDRAIL_NAME:
                existing_id = g["guardrailId"]
                break

    guardrail_config = dict(
        name=GUARDRAIL_NAME,
        description="MindScope report generation guardrail — blocks clinical/diagnostic content",
        topicPolicyConfig={
            "topicsConfig": [
                {
                    "name": "ClinicalDiagnosis",
                    "definition": (
                        "Clinical or psychiatric diagnoses, mental health disorder labels, "
                        "neurological or developmental condition assessments."
                    ),
                    "examples": [
                        "You may have ADHD",
                        "This suggests depression",
                        "You show signs of autism spectrum disorder",
                    ],
                    "type": "DENY",
                },
                {
                    "name": "MedicalAdvice",
                    "definition": (
                        "Medication recommendations, prescription guidance, therapy referrals, "
                        "or clinical treatment plans."
                    ),
                    "examples": [
                        "Consider antidepressants",
                        "You should see a psychiatrist",
                        "Try cognitive behavioral therapy",
                    ],
                    "type": "DENY",
                },
            ]
        },
        contentPolicyConfig={
            "filtersConfig": [
                {"type": "HATE",        "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "VIOLENCE",    "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "SELF_HARM",   "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "SEXUAL",      "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "INSULTS",     "inputStrength": "MEDIUM", "outputStrength": "HIGH"},
            ]
        },
        sensitiveInformationPolicyConfig={
            "piiEntitiesConfig": [
                {"type": "EMAIL",   "action": "ANONYMIZE"},
                {"type": "PHONE",   "action": "ANONYMIZE"},
                {"type": "US_SSN",  "action": "ANONYMIZE"},
            ]
        },
        blockedInputMessaging=(
            "I cannot process this request. Please use the MindScope assessment form to provide your information."
        ),
        blockedOutputsMessaging=(
            "This response was blocked by content policy. A support team member will review your report."
        ),
    )

    if existing_id:
        print(f"Updating existing guardrail {existing_id}...")
        resp = client.update_guardrail(guardrailId=existing_id, **guardrail_config)
        guardrail_id = existing_id
        guardrail_version = resp.get("version", "DRAFT")
    else:
        print("Creating new guardrail...")
        resp = client.create_guardrail(**guardrail_config)
        guardrail_id = resp["guardrailId"]
        guardrail_version = resp.get("version", "DRAFT")

    print(f"\nGuardrail created/updated successfully.")
    print(f"\nSet these in your ECS task definition / .env:")
    print(f"  BEDROCK_GUARDRAIL_ID={guardrail_id}")
    print(f"  BEDROCK_GUARDRAIL_VERSION={guardrail_version}")
    return guardrail_id, guardrail_version


if __name__ == "__main__":
    create_or_update()
