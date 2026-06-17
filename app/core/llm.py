"""
MindScope — LLM Service (LangChain + Bedrock)

Runtime-switchable model selection. No hardcoded model preferences.
Pass any Bedrock-supported model at call time.

Usage:
    from app.core.llm import llm_service

    # Use defaults (sonnet for questions, opus for reports)
    response = llm_service.generate_report(profile, intake)

    # Override model for this call
    response = llm_service.generate_report(profile, intake, model="sonnet")

    # Change defaults at runtime (e.g., from admin panel or env var)
    llm_service.set_default("report_generation", "sonnet")

    # Or just get a raw LangChain ChatModel for any Bedrock model
    chat = llm_service.get_chat_model("opus", temperature=0.5)
"""

from typing import Optional
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
import json


# ── Bedrock Model Registry ───────────────────────────────────────────────────
# Short name → Bedrock cross-region inference profile ID
# Must use us.* prefix — direct model IDs are not supported on-demand.
# Add any new Bedrock model here and it's instantly available everywhere.

BEDROCK_MODELS = {
    # Claude 4 family (cross-region inference profiles — verified working)
    "opus":       "us.anthropic.claude-opus-4-7",
    "sonnet":     "us.anthropic.claude-sonnet-4-6",
    "haiku":      "us.anthropic.claude-haiku-4-5-20251001-v1:0",

    # Claude 3.5 fallbacks
    "sonnet-3.5": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "haiku-3.5":  "us.anthropic.claude-3-5-haiku-20241022-v1:0",
}

PROMPT_TEMPLATE_VERSION = "pt-v1.0"


def _parse_json_response(content: str) -> dict:
    """Strip markdown code fences if present, then parse JSON."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence (```json or ```) and closing fence
        inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = inner.strip()
    return json.loads(text)


class LLMService:
    """
    Centralized LLM access for MindScope.

    - Wraps LangChain's ChatBedrockConverse
    - Any model can be swapped at call time via the `model` parameter
    - Defaults are stored in-memory and can be changed at runtime
    - Each pipeline stage has its own default model
    """

    def __init__(self, region: str = "us-east-1"):
        self.region = region

        # ── Default models per stage ──────────────────────────────────────
        self._defaults = {
            "question_generation":      "sonnet",
            "question_correction":      "sonnet",
            "question_personalization": "sonnet",
            "report_generation":        "opus",
            "report_summary":           "sonnet",
        }

        # ── Default temperatures per stage ───────────────────────────────
        self._temperatures = {
            "question_generation":      0.7,
            "question_correction":      0.2,
            "question_personalization": 0.4,
            "report_generation":        0.3,
            "report_summary":           0.3,
        }

        # ── Default max tokens per stage ─────────────────────────────────
        self._max_tokens = {
            "question_generation":      2048,
            "question_correction":      1024,
            "question_personalization": 2048,
            "report_generation":        4096,
            "report_summary":           512,
        }

        self._model_cache: dict[str, ChatBedrockConverse] = {}

    # ── Public: Change defaults at runtime ───────────────────────────────────

    def set_default(self, stage: str, model: str,
                    temperature: Optional[float] = None,
                    max_tokens: Optional[int] = None):
        if model not in BEDROCK_MODELS:
            raise ValueError(f"Unknown model '{model}'. Available: {list(BEDROCK_MODELS.keys())}")
        self._defaults[stage] = model
        if temperature is not None:
            self._temperatures[stage] = temperature
        if max_tokens is not None:
            self._max_tokens[stage] = max_tokens

    def get_defaults(self) -> dict:
        return {
            stage: {
                "model": self._defaults[stage],
                "model_id": BEDROCK_MODELS[self._defaults[stage]],
                "temperature": self._temperatures[stage],
                "max_tokens": self._max_tokens[stage],
            }
            for stage in self._defaults
        }

    # ── Public: Get a raw LangChain ChatModel ────────────────────────────────

    def get_chat_model(
        self,
        model: str = "sonnet",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> ChatBedrockConverse:
        if model not in BEDROCK_MODELS:
            raise ValueError(f"Unknown model '{model}'. Available: {list(BEDROCK_MODELS.keys())}")
        cache_key = f"{model}_{temperature}_{max_tokens}"
        if cache_key not in self._model_cache:
            self._model_cache[cache_key] = ChatBedrockConverse(
                model=BEDROCK_MODELS[model],
                region_name=self.region,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        return self._model_cache[cache_key]

    # ── Pipeline Stage Methods ────────────────────────────────────────────────

    def generate_report(
        self,
        profile: dict,
        intake: dict,
        model: Optional[str] = None,
    ) -> dict:
        """
        Generate the 5-section assessment report.
        Uses Opus by default — the product's main selling point.
        AI receives only the finished numeric profile — never raw item responses.
        """
        stage = "report_generation"
        chat = self._get_stage_model(stage, model)

        system_prompt = """You are an expert career counselor generating a personalized psychometric assessment report.

GROUNDING RULE (non-negotiable): Every interpretive sentence must reference exactly ONE specific score
AND exactly ONE specific intake-form value. No Barnum-style vague statements
("you have a unique blend of strengths..." is forbidden).

Output MUST be valid JSON with exactly these 5 keys:
{
    "snapshot": "3-4 sentence executive summary of the full profile. Ground each sentence.",
    "strengths": "Grounded in Big Five + Aptitude results. Reference specific percentiles.",
    "friction_points": "Honest, constructive. Name the gap between scores and stated goals.",
    "career_directions": ["3-5 RIASEC-driven directions. Each must name the top-code match and one intake value."],
    "next_steps": ["3 actionable suggestions. Each tied to a specific score AND a specific intake field."]
}

Compare scores against stated goals and current situation.
If there is alignment, reinforce it with the specific numbers.
If there is a gap, name it constructively with the specific numbers."""

        human_prompt = f"""User Profile (scores + intake):
{json.dumps(profile, indent=2)}

Intake Form:
{json.dumps(intake, indent=2)}"""

        response = chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        return _parse_json_response(response.content)

    def correct_questions(
        self,
        items: list[dict],
        model: Optional[str] = None,
    ) -> list[dict]:
        """Validate and correct generated items for quality."""
        stage = "question_correction"
        chat = self._get_stage_model(stage, model)

        system_prompt = """You are a psychometric quality reviewer.
Check each item for:
1. Double-barreled phrasing (two concepts in one item)
2. Ambiguous wording
3. Cultural/regional bias
4. Correct RIASEC subscale alignment
5. Likert-scale compatibility

Output JSON array: [{item_id, status: "pass"|"flag", issues: [], suggested_rewrite: "..."}]"""

        response = chat.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(items, indent=2)),
        ])

        return _parse_json_response(response.content)

    def generate_summary(
        self,
        profile: dict,
        model: Optional[str] = None,
    ) -> str:
        """Short 2-sentence teaser summary — used on report-ready screen."""
        stage = "report_summary"
        chat = self._get_stage_model(stage, model)

        response = chat.invoke([
            SystemMessage(content=(
                "Generate a 2-sentence career insight teaser from this RIASEC profile. "
                "Be specific — reference the top RIASEC code and one aptitude or Big Five score. "
                "No vague language."
            )),
            HumanMessage(content=json.dumps(profile, indent=2)),
        ])

        return response.content

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_stage_model(self, stage: str, override: Optional[str] = None) -> ChatBedrockConverse:
        model = override or self._defaults.get(stage, "sonnet")
        temperature = self._temperatures.get(stage, 0.3)
        max_tokens = self._max_tokens.get(stage, 4096)
        return self.get_chat_model(model, temperature, max_tokens)


# ── Singleton — import this everywhere ───────────────────────────────────────
llm_service = LLMService(region="us-east-1")
