import json
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.models.audit import AuditAISummary, AuditRun
from app.services.resilience import with_http_retries

settings = get_settings()
logger = get_logger(__name__)

SYSTEM_PROMPT = """
You are a Meta Ads audit explanation assistant.
You must only explain the structured data provided.
Rules:
- Do not calculate new metrics.
- Do not invent facts or values.
- Do not guarantee outcomes.
- Keep language business-friendly and concise.
- Explain why findings matter in business terms.
- If data is missing, explicitly say it is not provided.
Return strict JSON with keys:
short_executive_summary, detailed_audit_explanation, prioritized_action_plan.
""".strip()

SHORT_TEMPLATE = """
Write a 3-5 sentence executive summary for a business stakeholder.
Mention health score posture, estimated waste, top risk areas, and next-step urgency.
Do not include any metric not present in INPUT.
""".strip()

DETAILED_TEMPLATE = """
Write a concise but insightful detailed explanation of findings.
Group by severity and theme. Explain why each high-impact issue matters.
Tie statements only to values in INPUT.
""".strip()

ACTION_TEMPLATE = """
Write a prioritized action plan with 3-6 actions.
Each action should include: priority level, what to do, why it matters.
No guaranteed outcomes. No invented numbers.
""".strip()


class AISummaryService:
    @staticmethod
    def _severity_rank(level: str) -> int:
        order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return order.get(level, 0)

    @classmethod
    def _build_structured_input(cls, run: AuditRun) -> dict[str, Any]:
        data_mode = "period_aggregate" if run.analysis_start == run.analysis_end else "daily_breakdown"
        limitations: list[str] = []
        if data_mode == "period_aggregate":
            limitations.append("This audit was generated from an aggregate imported report rather than daily time-series data.")
            limitations.append("Trend and anomaly interpretations are limited for this run.")

        findings = sorted(
            [
                {
                    "rule_id": item.rule_id,
                    "severity": item.severity,
                    "category": item.category,
                    "title": item.title,
                    "description": item.description,
                    "entity_name": item.entity_name,
                    "estimated_waste": item.estimated_waste,
                    "estimated_uplift": item.estimated_uplift,
                }
                for item in run.findings
            ],
            key=lambda item: (cls._severity_rank(item["severity"]), item["estimated_waste"]),
            reverse=True,
        )

        opportunities = sorted(
            [
                {
                    "title": item.title,
                    "entity_name": item.entity_name,
                    "estimated_uplift": item.estimated_uplift,
                    "estimated_waste": item.estimated_waste,
                }
                for item in run.findings
            ],
            key=lambda item: item["estimated_uplift"],
            reverse=True,
        )[:5]

        return {
            "audit_run_id": run.id,
            "data_mode": data_mode,
            "limitations": limitations,
            "health_score": run.health_score,
            "total_spend": run.total_spend,
            "estimated_waste": run.total_wasted_spend,
            "estimated_uplift": run.total_estimated_uplift,
            "findings_count": run.findings_count,
            "analysis_window": {
                "start": run.analysis_start.isoformat(),
                "end": run.analysis_end.isoformat(),
            },
            "findings": findings,
            "top_opportunities": opportunities,
        }

    @staticmethod
    def _fallback_output(payload: dict[str, Any], reason: str | None = None) -> dict[str, str]:
        findings = payload.get("findings", [])
        top = findings[:3]
        top_lines = []
        for item in top:
            top_lines.append(
                f"- {item['title']} ({item['severity']}) on {item['entity_name']}: estimated waste {item['estimated_waste']:.0f}."
            )

        limitation_note = ""
        if payload.get("data_mode") == "period_aggregate":
            limitation_note = " The source file is an aggregate period report, so trend and anomaly commentary is limited."
        return {
            "short_executive_summary": (
                f"Health Score is {payload['health_score']:.1f} with estimated waste of {payload['estimated_waste']:.0f}."
                f" The audit surfaced {payload['findings_count']} deterministic findings.{limitation_note}"
            ),
            "detailed_audit_explanation": "\n".join(top_lines) if top_lines else "No findings were provided in this audit input.",
            "prioritized_action_plan": (
                "1. Address critical and high-severity findings first.\n"
                "2. Prioritize opportunities with the largest estimated uplift.\n"
                "3. Re-run sync and audit after changes to verify deterministic improvement."
            ),
        }

    @staticmethod
    def _validate_output(data: dict[str, Any]) -> dict[str, str]:
        required = [
            "short_executive_summary",
            "detailed_audit_explanation",
            "prioritized_action_plan",
        ]
        cleaned: dict[str, str] = {}
        for key in required:
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Missing or invalid summary field: {key}")
            cleaned[key] = value.strip()
        return cleaned

    @classmethod
    def _provider_request(cls, payload: dict[str, Any]) -> dict[str, str]:
        provider = settings.ai_provider.lower().strip()
        api_key = settings.ai_api_key.strip()

        if api_key and provider in {"", "mock", "none"}:
            provider = "openai"

        if not api_key or provider in {"mock", "none"}:
            return cls._fallback_output(payload, "provider not configured")

        if provider == "openai":
            return cls._openai_request(payload, api_key)
        if provider == "anthropic":
            return cls._anthropic_request(payload, api_key)
        if provider == "gemini":
            return cls._gemini_request(payload, api_key)

        return cls._fallback_output(payload, f"unknown provider {provider}")

    @classmethod
    def _openai_request(cls, payload: dict[str, Any], api_key: str) -> dict[str, str]:
        url = f"{settings.ai_openai_base_url.rstrip('/')}/chat/completions"
        user_prompt = (
            "INPUT JSON:\n"
            f"{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"TASK 1:\n{SHORT_TEMPLATE}\n\n"
            f"TASK 2:\n{DETAILED_TEMPLATE}\n\n"
            f"TASK 3:\n{ACTION_TEMPLATE}"
        )

        body = {
            "model": settings.ai_model,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }

        with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
            def _send():
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                )
                response.raise_for_status()
                return response.json()

            data = with_http_retries(_send, max_attempts=settings.ai_max_retries + 1)

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return cls._validate_output(parsed)

    @classmethod
    def _anthropic_request(cls, payload: dict[str, Any], api_key: str) -> dict[str, str]:
        url = f"{settings.ai_anthropic_base_url.rstrip('/')}/messages"
        user_prompt = (
            "INPUT JSON:\n"
            f"{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"TASK 1:\n{SHORT_TEMPLATE}\n\n"
            f"TASK 2:\n{DETAILED_TEMPLATE}\n\n"
            f"TASK 3:\n{ACTION_TEMPLATE}\n\n"
            "Return strict JSON only."
        )

        body = {
            "model": settings.ai_model,
            "max_tokens": 1200,
            "temperature": 0.1,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
            def _send():
                response = client.post(
                    url,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json=body,
                )
                response.raise_for_status()
                return response.json()

            data = with_http_retries(_send, max_attempts=settings.ai_max_retries + 1)

        text_blocks = [item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"]
        parsed = json.loads("".join(text_blocks).strip())
        return cls._validate_output(parsed)

    @classmethod
    def _gemini_request(cls, payload: dict[str, Any], api_key: str) -> dict[str, str]:
        url = f"{settings.ai_gemini_base_url.rstrip('/')}/models/{settings.ai_model}:generateContent"
        user_prompt = (
            "INPUT JSON:\n"
            f"{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"TASK 1:\n{SHORT_TEMPLATE}\n\n"
            f"TASK 2:\n{DETAILED_TEMPLATE}\n\n"
            f"TASK 3:\n{ACTION_TEMPLATE}\n\n"
            "Return strict JSON only."
        )

        body = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        with httpx.Client(timeout=float(settings.ai_timeout_seconds)) as client:
            def _send():
                response = client.post(
                    url,
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=body,
                )
                response.raise_for_status()
                return response.json()

            data = with_http_retries(_send, max_attempts=settings.ai_max_retries + 1)

        parts = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        text = "".join(part.get("text", "") for part in parts).strip()
        parsed = json.loads(text)
        return cls._validate_output(parsed)

    @classmethod
    def _generate_with_retries(cls, payload: dict[str, Any]) -> dict[str, str]:
        # HTTP retries are handled in provider-specific requests.
        return cls._provider_request(payload)

    @classmethod
    def get_for_run(cls, db: Session, audit_run_id: str) -> AuditAISummary | None:
        return db.query(AuditAISummary).filter(AuditAISummary.audit_run_id == audit_run_id).first()

    @classmethod
    def generate_for_run(
        cls,
        db: Session,
        run: AuditRun,
        regenerate: bool = False,
    ) -> AuditAISummary:
        existing = cls.get_for_run(db, run.id)
        if existing and not regenerate and existing.status == "completed":
            return existing

        payload = cls._build_structured_input(run)
        payload_json = json.dumps(payload, ensure_ascii=True)

        summary = existing or AuditAISummary(
            audit_run_id=run.id,
            provider=settings.ai_provider,
            model=settings.ai_model,
            prompt_version=settings.ai_prompt_version,
            status="pending",
            short_executive_summary="",
            detailed_audit_explanation="",
            prioritized_action_plan="",
            input_payload_json=payload_json,
        )

        summary.provider = settings.ai_provider
        summary.model = settings.ai_model
        summary.prompt_version = settings.ai_prompt_version
        summary.input_payload_json = payload_json
        summary.error_message = None

        try:
            output = cls._generate_with_retries(payload)
            summary.short_executive_summary = output["short_executive_summary"]
            summary.detailed_audit_explanation = output["detailed_audit_explanation"]
            summary.prioritized_action_plan = output["prioritized_action_plan"]
            summary.status = "completed"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ai.summary_generation_failed",
                extra={"audit_run_id": run.id, "code": "AI_SUMMARY_FALLBACK"},
            )
            fallback = cls._fallback_output(payload, str(exc))
            summary.short_executive_summary = fallback["short_executive_summary"]
            summary.detailed_audit_explanation = fallback["detailed_audit_explanation"]
            summary.prioritized_action_plan = fallback["prioritized_action_plan"]
            summary.status = "failed"
            summary.error_message = f"{type(exc).__name__}: {str(exc)[:1800]}"

        db.add(summary)
        db.commit()
        db.refresh(summary)
        return summary
