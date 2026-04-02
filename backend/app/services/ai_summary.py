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
Only explain the structured data provided — never invent metrics, values, or outcomes.
Keep language business-friendly and concise.
Return strict JSON with exactly three string keys:
  short_executive_summary, detailed_audit_explanation, prioritized_action_plan.
""".strip()

SHORT_TEMPLATE = """
TASK 1 — short_executive_summary:
3-5 sentences for a business stakeholder. Cover health score posture, estimated waste,
top 1-2 risk areas, and urgency. Only cite metrics present in INPUT.
""".strip()

DETAILED_TEMPLATE = """
TASK 2 — detailed_audit_explanation:
Concise explanation grouped by severity. For each critical/high finding explain
why it is costing money. Reference entity names and metric values from INPUT only.
""".strip()

ACTION_TEMPLATE = """
TASK 3 — prioritized_action_plan:
3-6 numbered actions ordered by estimated_waste descending. Each action MUST include:
- Priority level (Critical / High / Medium)
- Exact entity name from INPUT
- Actual metric vs threshold (if available in INPUT)
- One sentence: why this is losing money or reducing efficiency
- "Why it matters: [reason]"
- "Next step: [one concrete action, e.g. pause campaign, refresh creatives, tighten audience]"
Never use vague phrases. Never guarantee outcomes. Only reference values from INPUT.
""".strip()


class AISummaryService:
    GENERIC_ACTION_PLAN_PHRASES = (
        "address critical and high-severity findings first",
        "prioritize opportunities with the largest estimated uplift",
        "re-run sync and audit",
        "address high-severity findings first",
        "review your campaigns",
        "optimize your ads",
        "improve performance",
        "monitor closely",
        "consider reviewing",
        "take immediate action",
    )

    @staticmethod
    def _extract_json_text(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1]
        return cleaned

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, list):
            lines: list[str] = []
            for index, item in enumerate(value, start=1):
                if isinstance(item, str):
                    text = item.strip()
                elif isinstance(item, dict):
                    label = item.get("title") or item.get("action") or item.get("priority") or item.get("summary")
                    detail = item.get("why") or item.get("reason") or item.get("details") or item.get("description")
                    text = " - ".join(part for part in [label, detail] if isinstance(part, str) and part.strip())
                else:
                    text = str(item).strip()
                if text:
                    lines.append(f"{index}. {text}" if len(value) > 1 else text)
            return "\n".join(lines).strip()
        if isinstance(value, dict):
            lines = []
            for key, item in value.items():
                rendered = AISummaryService._stringify_value(item)
                if rendered:
                    label = str(key).replace("_", " ").strip().capitalize()
                    lines.append(f"{label}: {rendered}")
            return "\n".join(lines).strip()
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _severity_rank(level: str) -> int:
        order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return order.get(level, 0)

    @classmethod
    def _build_structured_input(cls, run: AuditRun) -> dict[str, Any]:
        data_mode = "period_aggregate" if run.analysis_start == run.analysis_end else "daily_breakdown"
        limitations: list[str] = []
        if data_mode == "period_aggregate":
            limitations.append("Aggregate report — trend analysis is limited.")

        recommendation_by_finding_id = {
            item.audit_finding_id: item
            for item in run.recommendations
            if item.audit_finding_id
        }

        HIGH_SEVERITY = {"critical", "high"}
        _DESC_TRUNCATE_LOW = 120  # chars for medium/low severity descriptions

        all_findings = sorted(
            run.findings,
            key=lambda item: (cls._severity_rank(item.severity), item.estimated_waste or 0),
            reverse=True,
        )

        findings = []
        for item in all_findings:
            rec = recommendation_by_finding_id.get(item.id)
            description = item.description or ""
            # Truncate descriptions for non-critical findings to reduce token waste
            if item.severity not in HIGH_SEVERITY and len(description) > _DESC_TRUNCATE_LOW:
                description = description[:_DESC_TRUNCATE_LOW].rsplit(" ", 1)[0] + "…"

            findings.append({
                "rule_id": item.rule_id,
                "severity": item.severity,
                "category": item.category,
                "title": item.title,
                "description": description,
                "entity_name": item.entity_name,
                "metric_value": item.metric_value,
                "threshold_value": item.threshold_value,
                "estimated_waste": item.estimated_waste,
                "estimated_uplift": item.estimated_uplift,
                "recommendation": rec.title if rec else None,
                "recommendation_title": rec.title if rec else None,
                "recommendation_body": rec.body if rec else None,
            })

        return {
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
        }

    @staticmethod
    def _is_percentage_metric(item: dict[str, Any]) -> bool:
        category = str(item.get("category") or "").lower()
        rule_id = str(item.get("rule_id") or "").lower()
        title = str(item.get("title") or "").lower()

        if category == "ctr" or "ctr" in rule_id or "ctr" in title:
            return True
        if "conversion rate" in title or "cvr" in rule_id or "cvr" in title:
            return True
        return False

    @classmethod
    def _format_metric_for_summary(cls, value: Any, item: dict[str, Any]) -> str | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        normalized = str(item.get("category") or "").lower()
        if cls._is_percentage_metric(item):
            return f"{numeric:.2f}%"
        if normalized in {"budget", "cpa", "spend"} or any(token in normalized for token in ("spend", "cpa", "cpc", "cpm")):
            return f"${numeric:.2f}"
        if normalized == "frequency":
            return f"{numeric:.2f}x"
        return f"{numeric:.2f}"

    @staticmethod
    def _clean_sentence(text: str | None, fallback: str) -> str:
        value = (text or "").strip()
        if not value:
            return fallback
        value = " ".join(value.split())
        value = value.rstrip(".")
        return f"{value}."

    @staticmethod
    def _title_case_severity(level: str | None) -> str:
        value = (level or "").strip().lower()
        if not value:
            return "Priority"
        return value.capitalize()

    # Category → specific next-step guidance
    _CATEGORY_NEXT_STEPS: dict[str, str] = {
        "ctr": "Refresh ad creatives, test new hooks or headlines, and narrow the target audience to improve click relevance.",
        "cpa": "Review bid strategy (switch to cost cap or target CPA), tighten the audience, and pause the highest-CPA ad sets.",
        "budget": "Reallocate daily budget from underperforming campaigns toward the highest-ROAS campaigns in the account.",
        "spend": "Review lifetime vs. daily budget settings and check whether pacing is set to standard or accelerated delivery.",
        "frequency": "Expand the audience, rotate creatives, or reduce the campaign's daily budget to lower impression frequency.",
        "trend": "Pull the last 14 days of daily data and compare CTR, CPA, and ROAS week-over-week to confirm the direction.",
        "performance": "Audit the landing page experience and funnel tracking: confirm the pixel fires, check page load speed, and review the post-click flow.",
        "structure": "Review campaign objectives and ensure each campaign has a clear, single purpose aligned to its optimization goal.",
        "opportunity": "Compare ad set performance within this campaign and shift budget toward the highest-converting ad sets.",
        "placement": "Break out automatic placements into manual placement ad sets and pause high-CPM, low-CTR placements.",
        "account": "Run an account-level audit on CTR and conversion rate across all active campaigns to confirm whether this is isolated or systemic.",
        "conversion": "Verify the Meta pixel is firing correctly on all conversion events, and check for funnel drop-off in Ads Manager attribution.",
        "weak_cvr": "Test the landing page with heatmap tools, confirm the offer is visible above the fold, and check the form or checkout flow for friction.",
        "uneven_daily_spend": "Switch to a daily budget and set bid cap to reduce delivery spikes, or review pacing settings in campaign budget optimization.",
    }

    @classmethod
    def _next_step_for_finding(cls, item: dict[str, Any]) -> str:
        """Return a specific next-step string based on category and recommendation title."""
        category = (item.get("category") or "").lower()
        rule_id = (item.get("rule_id") or "").lower()
        # Use recommendation title (formerly body) for keyword matching
        recommendation_hint = (
            item.get("recommendation_body")
            or item.get("linked_recommendation_body")
            or item.get("recommendation_title")
            or item.get("recommendation")
            or ""
        ).lower()

        # Rule-ID-specific overrides first
        if "weak_cvr" in rule_id:
            return cls._CATEGORY_NEXT_STEPS["weak_cvr"]
        if "uneven_daily_spend" in rule_id:
            return cls._CATEGORY_NEXT_STEPS["uneven_daily_spend"]

        # Recommendation keyword overrides
        if "landing" in recommendation_hint:
            return "Inspect the landing page experience, offer alignment, and tracking path — confirm the pixel fires on the conversion event."
        if "creative" in recommendation_hint:
            return "Refresh creatives: test a new hook, headline, and visual for this campaign and pause the lowest-CTR ad variants."
        if "reallocat" in recommendation_hint or "budget" in recommendation_hint:
            return "Reallocate budget from this campaign toward the highest-ROAS campaign in the account."

        # Category fallback
        for key, guidance in cls._CATEGORY_NEXT_STEPS.items():
            if key in category or key in rule_id:
                return guidance

        return "Open Ads Manager, filter by this campaign, and review delivery, CTR, and conversion rate over the last 14 days."

    @classmethod
    def _fallback_action_plan(cls, payload: dict[str, Any]) -> str:
        findings = payload.get("findings", [])
        if not findings:
            return (
                "1. Confirm the imported report covers at least 30 days with daily rows.\n"
                "2. Review the dashboard evidence to verify where efficiency is breaking.\n"
                "3. Re-run the audit after the next data refresh to compare the account health score."
            )

        # Sort by estimated waste descending for maximum impact ordering
        findings = sorted(findings, key=lambda f: f.get("estimated_waste", 0), reverse=True)[:5]

        actions: list[str] = []
        for index, item in enumerate(findings, start=1):
            severity = cls._title_case_severity(item.get("severity"))
            entity_name = item.get("entity_name") or "the affected entity"
            actual = cls._format_metric_for_summary(item.get("metric_value"), item)
            threshold = cls._format_metric_for_summary(item.get("threshold_value"), item)
            waste = item.get("estimated_waste", 0)

            metric_text = ""
            if actual and threshold:
                metric_text = f"Actual is {actual} versus the threshold of {threshold}."
            elif actual:
                metric_text = f"Actual value is {actual}."

            waste_text = f" Estimated waste: ${waste:.0f}." if waste > 0 else ""

            recommendation_title = (
                item.get("recommendation_title")
                or item.get("recommendation")
                or item.get("linked_recommendation_title")
                or item.get("title")
                or "Review this issue"
            )
            why_it_matters = cls._clean_sentence(
                item.get("description"),
                "This issue is directly reducing account efficiency.",
            )
            next_step = cls._next_step_for_finding(item)

            action_intro = f"{index}. {severity}: {recommendation_title} — {entity_name}."
            metric_clause = f" {metric_text}" if metric_text else ""
            actions.append(
                f"{action_intro}{metric_clause}{waste_text} "
                f"Why it matters: {why_it_matters} "
                f"Next step: {next_step}"
            )
        return "\n".join(actions)

    @classmethod
    def _fallback_output(cls, payload: dict[str, Any], reason: str | None = None) -> dict[str, str]:

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
            "prioritized_action_plan": cls._fallback_action_plan(payload),
        }

    @classmethod
    def _action_plan_is_generic(cls, value: str) -> bool:
        normalized = value.lower().strip()
        if not normalized:
            return True
        if len(normalized) < 60:
            return True
        if "next step:" not in normalized and "why it matters:" not in normalized:
            return True
        return any(phrase in normalized for phrase in cls.GENERIC_ACTION_PLAN_PHRASES)

    @classmethod
    def _normalize_output(cls, data: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
        fallback = cls._fallback_output(payload)
        aliases: dict[str, list[str]] = {
            "short_executive_summary": [
                "short_executive_summary",
                "executive_summary",
                "summary",
                "short_summary",
                "overview",
            ],
            "detailed_audit_explanation": [
                "detailed_audit_explanation",
                "detailed_explanation",
                "analysis",
                "why_performance_is_slipping",
                "detailed_summary",
                "findings_explanation",
            ],
            "prioritized_action_plan": [
                "prioritized_action_plan",
                "action_plan",
                "prioritized_actions",
                "top_actions",
                "recommendations",
                "next_actions",
            ],
        }

        cleaned: dict[str, str] = {}
        for canonical_key, candidates in aliases.items():
            value = ""
            for candidate in candidates:
                value = cls._stringify_value(data.get(candidate))
                if value:
                    break
            cleaned[canonical_key] = value or fallback[canonical_key]
        if cls._action_plan_is_generic(cleaned["prioritized_action_plan"]):
            cleaned["prioritized_action_plan"] = cls._fallback_action_plan(payload)
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
            f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"{SHORT_TEMPLATE}\n\n"
            f"{DETAILED_TEMPLATE}\n\n"
            f"{ACTION_TEMPLATE}"
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
        parsed = json.loads(cls._extract_json_text(content))
        return cls._normalize_output(parsed, payload)

    @classmethod
    def _anthropic_request(cls, payload: dict[str, Any], api_key: str) -> dict[str, str]:
        url = f"{settings.ai_anthropic_base_url.rstrip('/')}/messages"
        user_prompt = (
            f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"{SHORT_TEMPLATE}\n\n"
            f"{DETAILED_TEMPLATE}\n\n"
            f"{ACTION_TEMPLATE}\n\n"
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
        parsed = json.loads(cls._extract_json_text("".join(text_blocks).strip()))
        return cls._normalize_output(parsed, payload)

    # Gemini responseSchema enforces exact output structure, eliminating key aliasing needs
    _GEMINI_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "short_executive_summary": {"type": "string"},
            "detailed_audit_explanation": {"type": "string"},
            "prioritized_action_plan": {"type": "string"},
        },
        "required": ["short_executive_summary", "detailed_audit_explanation", "prioritized_action_plan"],
    }

    @classmethod
    def _gemini_request(cls, payload: dict[str, Any], api_key: str) -> dict[str, str]:
        url = f"{settings.ai_gemini_base_url.rstrip('/')}/models/{settings.ai_model}:generateContent"
        user_prompt = (
            f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=True)}\n\n"
            f"{SHORT_TEMPLATE}\n\n"
            f"{DETAILED_TEMPLATE}\n\n"
            f"{ACTION_TEMPLATE}"
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
                "responseSchema": cls._GEMINI_RESPONSE_SCHEMA,
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
        parsed = json.loads(cls._extract_json_text(text))
        return cls._normalize_output(parsed, payload)

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
