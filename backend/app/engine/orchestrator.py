from datetime import date

from sqlalchemy.orm import Session

from app.engine.collector import collect_account_data
from app.engine.recommendations import apply_recommendation
from app.engine.rules import get_all_rules
from app.engine.scoring import compute_scores
from app.engine.types import Finding, Severity
from app.models.audit import AuditFinding, AuditRun, AuditScore, Recommendation


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def run_audit(db: Session, ad_account_id: str, user_id: str) -> AuditRun:
    audit_run = AuditRun(
        user_id=user_id,
        ad_account_id=ad_account_id,
        health_score=0.0,
        total_spend=0.0,
        total_wasted_spend=0.0,
        total_estimated_uplift=0.0,
        findings_count=0,
        campaign_count=0,
        ad_set_count=0,
        ad_count=0,
        analysis_start=date.today(),
        analysis_end=date.today(),
    )
    db.add(audit_run)
    db.flush()
    return populate_audit_run(db, audit_run)


def populate_audit_run(db: Session, audit_run: AuditRun) -> AuditRun:
    ad_account_id = audit_run.ad_account_id
    user_id = audit_run.user_id
    snapshot = collect_account_data(db, ad_account_id)
    findings: list[Finding] = []
    for rule in get_all_rules():
        findings.extend(rule.evaluate(snapshot))

    findings = [apply_recommendation(finding) for finding in findings]
    findings.sort(key=lambda finding: SEVERITY_ORDER[finding.severity])

    health_score, scores = compute_scores(
        findings,
        account_description=f"Account spend ${snapshot.account.total_spend:.0f}, CTR {snapshot.account.ctr:.2f}% and ROAS {snapshot.account.roas:.2f}x.",
    )

    total_wasted = min(snapshot.account.total_spend, sum(finding.estimated_waste for finding in findings))
    total_uplift = sum(finding.estimated_uplift for finding in findings)

    audit_run.health_score = health_score
    audit_run.total_spend = snapshot.account.total_spend
    audit_run.total_wasted_spend = total_wasted
    audit_run.total_estimated_uplift = total_uplift
    audit_run.findings_count = len(findings)
    audit_run.campaign_count = snapshot.campaign_count
    audit_run.ad_set_count = snapshot.ad_set_count
    audit_run.ad_count = snapshot.ad_count
    audit_run.analysis_start = snapshot.analysis_start
    audit_run.analysis_end = snapshot.analysis_end

    for collection in (audit_run.findings, audit_run.scores, audit_run.recommendations):
        if collection:
            collection.clear()
    if audit_run.ai_summary is not None:
        db.delete(audit_run.ai_summary)
        db.flush()

    finding_rows: list[AuditFinding] = []
    for finding in findings:
        row = AuditFinding(
            audit_run_id=audit_run.id,
            rule_id=finding.rule_id,
            severity=finding.severity.value,
            category=finding.category.value,
            title=finding.title,
            description=finding.description,
            entity_type=finding.entity_type,
            entity_id=finding.entity_id,
            entity_name=finding.entity_name,
            metric_value=finding.metric_value,
            threshold_value=finding.threshold_value,
            estimated_waste=finding.estimated_waste,
            estimated_uplift=finding.estimated_uplift,
            recommendation_key=finding.recommendation_key,
            score_impact=finding.score_impact,
        )
        db.add(row)
        finding_rows.append(row)
    db.flush()

    recommendation_map = {}
    for row, finding in zip(finding_rows, findings):
        key = finding.recommendation_key or finding.rule_id
        if key in recommendation_map:
            continue
        recommendation = Recommendation(
            audit_run_id=audit_run.id,
            audit_finding_id=row.id,
            recommendation_key=key,
            title=finding.recommendation_title,
            body=finding.recommendation_body,
        )
        db.add(recommendation)
        recommendation_map[key] = recommendation

    for score in scores:
        db.add(AuditScore(
            audit_run_id=audit_run.id,
            score_key=score.key,
            label=score.label,
            score=score.score,
            weight=score.weight,
            details=score.details,
        ))

    db.commit()
    db.refresh(audit_run)
    return audit_run
