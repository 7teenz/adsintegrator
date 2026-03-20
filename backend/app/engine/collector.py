from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.engine.metrics import (
    calc_click_to_conversion_rate,
    calc_cpa,
    calc_cpc,
    calc_cpm,
    calc_ctr,
    calc_frequency,
    calc_roas,
    calc_spend_share,
    calc_wow_delta,
)
from app.engine.types import AccountAuditMetrics, AccountAuditSnapshot, AdSetAuditMetrics, CampaignAuditMetrics, DailyMetricPoint
from app.models.campaign import Ad, AdSet, Campaign
from app.models.insights import DailyAccountInsight, DailyAdSetInsight, DailyCampaignInsight


def collect_account_data(db: Session, ad_account_id: str, lookback_days: int = 30) -> AccountAuditSnapshot:
    latest_available = (
        db.query(DailyAccountInsight.date)
        .filter(DailyAccountInsight.ad_account_id == ad_account_id)
        .order_by(DailyAccountInsight.date.desc())
        .first()
    )
    earliest_available = (
        db.query(DailyAccountInsight.date)
        .filter(DailyAccountInsight.ad_account_id == ad_account_id)
        .order_by(DailyAccountInsight.date.asc())
        .first()
    )

    if latest_available:
        analysis_end = latest_available[0]
    else:
        analysis_end = date.today() - timedelta(days=1)

    if earliest_available:
        candidate_start = analysis_end - timedelta(days=lookback_days - 1)
        analysis_start = max(candidate_start, earliest_available[0])
    else:
        analysis_start = analysis_end - timedelta(days=lookback_days - 1)

    campaigns = db.query(Campaign).filter(Campaign.ad_account_id == ad_account_id).all()
    ad_sets = db.query(AdSet).filter(AdSet.ad_account_id == ad_account_id).all()
    ad_count = db.query(Ad).filter(Ad.ad_account_id == ad_account_id).count()

    account_rows = (
        db.query(DailyAccountInsight)
        .filter(
            DailyAccountInsight.ad_account_id == ad_account_id,
            DailyAccountInsight.date >= analysis_start,
            DailyAccountInsight.date <= analysis_end,
        )
        .order_by(DailyAccountInsight.date)
        .all()
    )
    account_daily = [_daily_point(row) for row in account_rows]
    account_metrics = _aggregate_account(account_daily)

    campaign_outputs: list[CampaignAuditMetrics] = []
    total_spend = account_metrics.total_spend

    for campaign in campaigns:
        rows = (
            db.query(DailyCampaignInsight)
            .filter(
                DailyCampaignInsight.campaign_id == campaign.id,
                DailyCampaignInsight.date >= analysis_start,
                DailyCampaignInsight.date <= analysis_end,
            )
            .order_by(DailyCampaignInsight.date)
            .all()
        )
        points = [_daily_point(row) for row in rows]
        ad_set_count = db.query(AdSet).filter(AdSet.campaign_id == campaign.id).count()
        campaign_ad_count = db.query(Ad).filter(Ad.ad_set_id.in_(db.query(AdSet.id).filter(AdSet.campaign_id == campaign.id))).count()
        campaign_outputs.append(_aggregate_campaign(campaign, points, total_spend, ad_set_count, campaign_ad_count))

    ad_set_outputs: list[AdSetAuditMetrics] = []
    spend_by_campaign = {}
    for campaign_metric in campaign_outputs:
        spend_by_campaign[campaign_metric.campaign_id] = campaign_metric.total_spend

    for ad_set in ad_sets:
        rows = (
            db.query(DailyAdSetInsight)
            .filter(
                DailyAdSetInsight.ad_set_id == ad_set.id,
                DailyAdSetInsight.date >= analysis_start,
                DailyAdSetInsight.date <= analysis_end,
            )
            .order_by(DailyAdSetInsight.date)
            .all()
        )
        points = [_daily_point(row) for row in rows]
        ad_set_outputs.append(_aggregate_ad_set(ad_set, points, spend_by_campaign.get(ad_set.meta_campaign_id, 0.0)))

    data_mode = "daily_breakdown"
    limitations: list[str] = []
    if len(account_rows) <= 1:
        data_mode = "period_aggregate"
        limitations.append("Uploaded report contains aggregate period totals rather than daily time series.")
        limitations.append("Trend, anomaly, and week-over-week rules are limited for this audit.")

    return AccountAuditSnapshot(
        ad_account_id=ad_account_id,
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        data_mode=data_mode,
        limitations=limitations,
        account=account_metrics,
        campaigns=campaign_outputs,
        ad_sets=ad_set_outputs,
        campaign_count=len(campaigns),
        ad_set_count=len(ad_sets),
        ad_count=ad_count,
    )


def _daily_point(row) -> DailyMetricPoint:
    cpa = calc_cpa(row.spend, row.conversions)
    return DailyMetricPoint(
        date=row.date,
        spend=row.spend,
        impressions=row.impressions,
        clicks=row.clicks,
        conversions=row.conversions,
        conversion_value=row.conversion_value,
        ctr=row.ctr,
        cpc=row.cpc,
        cpm=row.cpm,
        frequency=row.frequency,
        roas=row.roas,
        cpa=cpa,
    )


def _aggregate_account(points: list[DailyMetricPoint]) -> AccountAuditMetrics:
    spends = [point.spend for point in points]
    ctrs = [point.ctr for point in points]
    roas_values = [point.roas for point in points]
    cpas = [point.cpa for point in points if point.cpa > 0]
    total_spend = sum(point.spend for point in points)
    total_impressions = sum(point.impressions for point in points)
    total_clicks = sum(point.clicks for point in points)
    total_reach = sum(point.impressions / point.frequency for point in points if point.frequency > 0)
    total_conversions = sum(point.conversions for point in points)
    total_conversion_value = sum(point.conversion_value for point in points)

    return AccountAuditMetrics(
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_reach=int(total_reach),
        total_conversions=total_conversions,
        total_conversion_value=total_conversion_value,
        ctr=calc_ctr(total_clicks, total_impressions),
        cpc=calc_cpc(total_spend, total_clicks),
        cpm=calc_cpm(total_spend, total_impressions),
        cpa=calc_cpa(total_spend, total_conversions),
        roas=calc_roas(total_conversion_value, total_spend),
        frequency=calc_frequency(total_impressions, int(total_reach)),
        click_to_conversion_rate=calc_click_to_conversion_rate(total_conversions, total_clicks),
        wow_spend_delta=calc_wow_delta(spends),
        wow_ctr_delta=calc_wow_delta(ctrs),
        wow_roas_delta=calc_wow_delta(roas_values),
        wow_cpa_delta=calc_wow_delta(cpas) if len(cpas) >= 14 else 0.0,
        daily_points=points,
    )


def _aggregate_campaign(campaign: Campaign, points: list[DailyMetricPoint], total_spend: float, ad_set_count: int, ad_count: int) -> CampaignAuditMetrics:
    spends = [point.spend for point in points]
    ctrs = [point.ctr for point in points]
    roas_values = [point.roas for point in points]
    cpas = [point.cpa for point in points if point.cpa > 0]
    spend = sum(point.spend for point in points)
    impressions = sum(point.impressions for point in points)
    clicks = sum(point.clicks for point in points)
    conversions = sum(point.conversions for point in points)
    conversion_value = sum(point.conversion_value for point in points)
    reach = sum(point.impressions / point.frequency for point in points if point.frequency > 0)
    return CampaignAuditMetrics(
        campaign_id=campaign.meta_campaign_id,
        campaign_name=campaign.name,
        status=campaign.status or "UNKNOWN",
        objective=campaign.objective,
        total_spend=spend,
        total_impressions=impressions,
        total_clicks=clicks,
        total_reach=int(reach),
        total_conversions=conversions,
        total_conversion_value=conversion_value,
        ctr=calc_ctr(clicks, impressions),
        cpc=calc_cpc(spend, clicks),
        cpm=calc_cpm(spend, impressions),
        cpa=calc_cpa(spend, conversions),
        roas=calc_roas(conversion_value, spend),
        frequency=calc_frequency(impressions, int(reach)),
        click_to_conversion_rate=calc_click_to_conversion_rate(conversions, clicks),
        spend_share=calc_spend_share(spend, total_spend),
        wow_spend_delta=calc_wow_delta(spends),
        wow_ctr_delta=calc_wow_delta(ctrs),
        wow_roas_delta=calc_wow_delta(roas_values),
        wow_cpa_delta=calc_wow_delta(cpas) if len(cpas) >= 14 else 0.0,
        ad_set_count=ad_set_count,
        ad_count=ad_count,
        daily_points=points,
    )


def _aggregate_ad_set(ad_set: AdSet, points: list[DailyMetricPoint], campaign_spend: float) -> AdSetAuditMetrics:
    spends = [point.spend for point in points]
    ctrs = [point.ctr for point in points]
    roas_values = [point.roas for point in points]
    cpas = [point.cpa for point in points if point.cpa > 0]
    spend = sum(point.spend for point in points)
    impressions = sum(point.impressions for point in points)
    clicks = sum(point.clicks for point in points)
    conversions = sum(point.conversions for point in points)
    conversion_value = sum(point.conversion_value for point in points)
    reach = sum(point.impressions / point.frequency for point in points if point.frequency > 0)
    return AdSetAuditMetrics(
        ad_set_id=ad_set.meta_adset_id,
        ad_set_name=ad_set.name,
        campaign_id=ad_set.meta_campaign_id,
        campaign_name=ad_set.campaign.name if ad_set.campaign else ad_set.meta_campaign_id,
        status=ad_set.status or "UNKNOWN",
        optimization_goal=ad_set.optimization_goal,
        total_spend=spend,
        total_impressions=impressions,
        total_clicks=clicks,
        total_reach=int(reach),
        total_conversions=conversions,
        total_conversion_value=conversion_value,
        ctr=calc_ctr(clicks, impressions),
        cpc=calc_cpc(spend, clicks),
        cpm=calc_cpm(spend, impressions),
        cpa=calc_cpa(spend, conversions),
        roas=calc_roas(conversion_value, spend),
        frequency=calc_frequency(impressions, int(reach)),
        click_to_conversion_rate=calc_click_to_conversion_rate(conversions, clicks),
        spend_share_within_campaign=calc_spend_share(spend, campaign_spend),
        wow_spend_delta=calc_wow_delta(spends),
        wow_ctr_delta=calc_wow_delta(ctrs),
        wow_roas_delta=calc_wow_delta(roas_values),
        wow_cpa_delta=calc_wow_delta(cpas) if len(cpas) >= 14 else 0.0,
        daily_points=points,
    )
