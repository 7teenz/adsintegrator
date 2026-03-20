"""
Deterministic Audit Engine
===========================

Pure business logic — no LLM, no ORM in core.
Reads aggregated metrics, runs rules, produces a report.

Usage:
    from app.engine.orchestrator import run_audit
    report = run_audit(db, ad_account_id)
"""
