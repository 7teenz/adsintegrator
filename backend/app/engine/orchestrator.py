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

    audit_run = AuditRun(
        user_id=user_id,
        ad_account_id=ad_account_id,
        health_score=health_score,
        total_spend=snapshot.account.total_spend,
        total_wasted_spend=total_wasted,
        total_estimated_uplift=total_uplift,
        findings_count=len(findings),
        campaign_count=snapshot.campaign_count,
        ad_set_count=snapshot.ad_set_count,
        ad_count=snapshot.ad_count,
        analysis_start=snapshot.analysis_start,
        analysis_end=snapshot.analysis_end,
    )
    db.add(audit_run)
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
