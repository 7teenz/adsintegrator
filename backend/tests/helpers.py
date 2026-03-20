from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.audit import AuditFinding, AuditRun, AuditScore, Recommendation
from app.models.campaign import Ad, AdSet, Campaign
from app.models.insights import DailyAccountInsight, DailyAdSetInsight, DailyCampaignInsight
from app.models.meta_connection import MetaAdAccount, MetaConnection
from app.models.user import User
from app.services.auth import create_access_token, hash_password


def create_user(db: Session, email: str = "user@example.com", password: str = "secret123") -> User:
    user = User(email=email, hashed_password=hash_password(password), full_name="Test User")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header_for_user(user_id: str) -> dict[str, str]:
    token = create_access_token({"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


def seed_connected_account(db: Session, user: User) -> MetaAdAccount:
    connection = MetaConnection(
        user_id=user.id,
        meta_user_id="meta_user_1",
        meta_user_name="Meta User",
        encrypted_access_token="encrypted",
    )
    db.add(connection)
    db.flush()
    account = MetaAdAccount(
        connection_id=connection.id,
        account_id="act_123",
        account_name="Main Account",
        is_selected=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def seed_audit_data(db: Session, account: MetaAdAccount) -> None:
    campaign = Campaign(
        ad_account_id=account.id,
        meta_campaign_id="cmp_1",
        name="Campaign One",
        objective="CONVERSIONS",
        status="ACTIVE",
    )
    db.add(campaign)
    db.flush()
    ad_set = AdSet(
        campaign_id=campaign.id,
        ad_account_id=account.id,
        meta_adset_id="adset_1",
        meta_campaign_id=campaign.meta_campaign_id,
        name="Ad Set One",
        optimization_goal="OFFSITE_CONVERSIONS",
        status="ACTIVE",
    )
    db.add(ad_set)
    db.flush()
    ad = Ad(
        ad_set_id=ad_set.id,
        ad_account_id=account.id,
        meta_ad_id="ad_1",
        meta_adset_id=ad_set.meta_adset_id,
        name="Ad One",
        status="ACTIVE",
    )
    db.add(ad)
    db.flush()

    base_date = date.today() - timedelta(days=10)
    for idx in range(10):
        day = base_date + timedelta(days=idx)
        db.add(
            DailyAccountInsight(
                ad_account_id=account.id,
                date=day,
                impressions=1000 + idx * 50,
                clicks=30 + idx,
                spend=40 + idx * 2,
                reach=700 + idx * 30,
                ctr=2.0,
                cpc=1.4,
                cpm=40.0,
                frequency=1.5,
                conversions=2 + (idx % 2),
                conversion_value=55 + idx * 2,
                roas=1.2,
            )
        )
        db.add(
            DailyCampaignInsight(
                ad_account_id=account.id,
                campaign_id=campaign.id,
                date=day,
                impressions=1000 + idx * 50,
                clicks=30 + idx,
                spend=40 + idx * 2,
                reach=700 + idx * 30,
                ctr=2.0,
                cpc=1.4,
                cpm=40.0,
                frequency=1.5,
                conversions=2 + (idx % 2),
                conversion_value=55 + idx * 2,
                roas=1.2,
            )
        )
        db.add(
            DailyAdSetInsight(
                ad_account_id=account.id,
                ad_set_id=ad_set.id,
                date=day,
                impressions=1000 + idx * 50,
                clicks=30 + idx,
                spend=40 + idx * 2,
                reach=700 + idx * 30,
                ctr=2.0,
                cpc=1.4,
                cpm=40.0,
                frequency=1.5,
                conversions=2 + (idx % 2),
                conversion_value=55 + idx * 2,
                roas=1.2,
            )
        )
    db.commit()


def seed_audit_run_with_findings(db: Session, user_id: str, account_id: str, count: int = 5) -> AuditRun:
    run = AuditRun(
        user_id=user_id,
        ad_account_id=account_id,
        health_score=62.0,
        total_spend=1000.0,
        total_wasted_spend=220.0,
        total_estimated_uplift=180.0,
        findings_count=count,
        campaign_count=1,
        ad_set_count=1,
        ad_count=1,
        analysis_start=date.today() - timedelta(days=30),
        analysis_end=date.today() - timedelta(days=1),
    )
    db.add(run)
    db.flush()
    severities = ["critical", "high", "medium", "low", "low"]
    for idx in range(count):
        finding = AuditFinding(
            audit_run_id=run.id,
            rule_id=f"rule_{idx}",
            severity=severities[idx % len(severities)],
            category="performance",
            title=f"Finding {idx}",
            description="Issue detail",
            entity_type="campaign",
            entity_id="cmp_1",
            entity_name="Campaign One",
            metric_value=1.0,
            threshold_value=2.0,
            estimated_waste=20.0 + idx,
            estimated_uplift=15.0 + idx,
            recommendation_key=f"rec_{idx}",
            score_impact=5.0,
        )
        db.add(finding)
        db.flush()
        db.add(
            Recommendation(
                audit_run_id=run.id,
                audit_finding_id=finding.id,
                recommendation_key=f"rec_{idx}",
                title=f"Recommendation {idx}",
                body="Action body",
            )
        )
    db.add(
        AuditScore(
            audit_run_id=run.id,
            score_key="acquisition",
            label="Acquisition",
            score=60.0,
            weight=0.5,
            details="Details",
        )
    )
    db.commit()
    db.refresh(run)
    return run
