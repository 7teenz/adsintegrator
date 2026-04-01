"""
Shared fixture builders for engine rule tests.

All builders return plain Python dataclasses — no database required.
Rules only depend on AccountAuditSnapshot and its nested metric objects.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.engine.types import (
    AccountAuditMetrics,
    AccountAuditSnapshot,
    AdSetAuditMetrics,
    CampaignAuditMetrics,
    DailyMetricPoint,
)

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

_BASE_DATE = date(2025, 1, 1)


def make_daily_points(
    n: int,
    *,
    ctr: float = 2.0,
    frequency: float = 2.0,
    spend_per_day: float = 50.0,
    impressions_per_day: int = 5000,
    clicks_per_day: int = 100,
    conversions_per_day: int = 5,
    roas: float = 3.0,
    cpm: float = 10.0,
) -> list[DailyMetricPoint]:
    return [
        DailyMetricPoint(
            date=_BASE_DATE + timedelta(days=i),
            spend=spend_per_day,
            impressions=impressions_per_day,
            clicks=clicks_per_day,
            conversions=conversions_per_day,
            conversion_value=spend_per_day * roas,
            ctr=ctr,
            cpc=spend_per_day / max(clicks_per_day, 1),
            cpm=cpm,
            frequency=frequency,
            roas=roas,
            cpa=spend_per_day / max(conversions_per_day, 1),
        )
        for i in range(n)
    ]


def make_declining_ctr_points(n: int = 28, start_ctr: float = 2.5, end_ctr: float = 1.0) -> list[DailyMetricPoint]:
    """Daily points whose CTR linearly declines from start_ctr to end_ctr."""
    step = (end_ctr - start_ctr) / max(n - 1, 1)
    return [
        DailyMetricPoint(
            date=_BASE_DATE + timedelta(days=i),
            spend=50.0,
            impressions=5000,
            clicks=int(5000 * (start_ctr + step * i) / 100),
            conversions=5,
            conversion_value=150.0,
            ctr=start_ctr + step * i,
            cpc=0.5,
            cpm=10.0,
            frequency=2.0,
            roas=3.0,
            cpa=10.0,
        )
        for i in range(n)
    ]


def make_spiking_frequency_points(n: int = 28) -> list[DailyMetricPoint]:
    """Daily points where frequency spikes sharply in the final 7 days.

    The first (n-7) days sit at low frequency (1.0) so that prev_7 is
    entirely in the calm zone, making the spike clearly > 1.5× threshold.
    """
    points = []
    low_days = n - 7
    for i in range(n):
        freq = 1.0 if i < low_days else 4.0
        points.append(DailyMetricPoint(
            date=_BASE_DATE + timedelta(days=i),
            spend=50.0,
            impressions=5000,
            clicks=100,
            conversions=5,
            conversion_value=150.0,
            ctr=2.0,
            cpc=0.5,
            cpm=10.0,
            frequency=freq,
            roas=3.0,
            cpa=10.0,
        ))
    return points


# ---------------------------------------------------------------------------
# Campaign / ad-set / account factories with sensible defaults
# ---------------------------------------------------------------------------

def make_campaign(
    campaign_id: str = "cmp_1",
    campaign_name: str = "Campaign 1",
    status: str = "ACTIVE",
    objective: str | None = "CONVERSIONS",
    total_spend: float = 1000.0,
    total_impressions: int = 50_000,
    total_clicks: int = 1500,
    total_reach: int = 40_000,
    total_conversions: int = 50,
    total_conversion_value: float = 3000.0,
    ctr: float = 3.0,
    cpc: float = 0.67,
    cpm: float = 20.0,
    cpa: float = 20.0,
    roas: float = 3.0,
    frequency: float = 2.0,
    click_to_conversion_rate: float = 3.3,
    spend_share: float = 0.5,
    wow_spend_delta: float = 0.05,
    wow_ctr_delta: float = 0.0,
    wow_roas_delta: float = 0.0,
    wow_cpa_delta: float = 0.0,
    ad_set_count: int = 2,
    ad_count: int = 6,
    daily_points: list[DailyMetricPoint] | None = None,
) -> CampaignAuditMetrics:
    return CampaignAuditMetrics(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        status=status,
        objective=objective,
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_reach=total_reach,
        total_conversions=total_conversions,
        total_conversion_value=total_conversion_value,
        ctr=ctr,
        cpc=cpc,
        cpm=cpm,
        cpa=cpa,
        roas=roas,
        frequency=frequency,
        click_to_conversion_rate=click_to_conversion_rate,
        spend_share=spend_share,
        wow_spend_delta=wow_spend_delta,
        wow_ctr_delta=wow_ctr_delta,
        wow_roas_delta=wow_roas_delta,
        wow_cpa_delta=wow_cpa_delta,
        ad_set_count=ad_set_count,
        ad_count=ad_count,
        daily_points=daily_points if daily_points is not None else make_daily_points(30),
    )


def make_adset(
    ad_set_id: str = "adset_1",
    ad_set_name: str = "Ad Set 1",
    campaign_id: str = "cmp_1",
    campaign_name: str = "Campaign 1",
    status: str = "ACTIVE",
    optimization_goal: str | None = "CONVERSIONS",
    total_spend: float = 500.0,
    total_impressions: int = 25_000,
    total_clicks: int = 750,
    total_reach: int = 20_000,
    total_conversions: int = 25,
    total_conversion_value: float = 1500.0,
    ctr: float = 3.0,
    cpc: float = 0.67,
    cpm: float = 20.0,
    cpa: float = 20.0,
    roas: float = 3.0,
    frequency: float = 2.0,
    click_to_conversion_rate: float = 3.3,
    spend_share_within_campaign: float = 0.5,
    wow_spend_delta: float = 0.05,
    wow_ctr_delta: float = 0.0,
    wow_roas_delta: float = 0.0,
    wow_cpa_delta: float = 0.0,
    daily_points: list[DailyMetricPoint] | None = None,
) -> AdSetAuditMetrics:
    return AdSetAuditMetrics(
        ad_set_id=ad_set_id,
        ad_set_name=ad_set_name,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        status=status,
        optimization_goal=optimization_goal,
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_reach=total_reach,
        total_conversions=total_conversions,
        total_conversion_value=total_conversion_value,
        ctr=ctr,
        cpc=cpc,
        cpm=cpm,
        cpa=cpa,
        roas=roas,
        frequency=frequency,
        click_to_conversion_rate=click_to_conversion_rate,
        spend_share_within_campaign=spend_share_within_campaign,
        wow_spend_delta=wow_spend_delta,
        wow_ctr_delta=wow_ctr_delta,
        wow_roas_delta=wow_roas_delta,
        wow_cpa_delta=wow_cpa_delta,
        daily_points=daily_points if daily_points is not None else [],
    )


def make_account(
    total_spend: float = 2000.0,
    total_impressions: int = 100_000,
    total_clicks: int = 3000,
    total_reach: int = 80_000,
    total_conversions: int = 100,
    total_conversion_value: float = 6000.0,
    ctr: float = 3.0,
    cpc: float = 0.67,
    cpm: float = 20.0,
    cpa: float = 20.0,
    roas: float = 3.0,
    frequency: float = 2.0,
    click_to_conversion_rate: float = 3.3,
    wow_spend_delta: float = 0.05,
    wow_ctr_delta: float = 0.0,
    wow_roas_delta: float = 0.0,
    wow_cpa_delta: float = 0.0,
    daily_points: list[DailyMetricPoint] | None = None,
) -> AccountAuditMetrics:
    return AccountAuditMetrics(
        total_spend=total_spend,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_reach=total_reach,
        total_conversions=total_conversions,
        total_conversion_value=total_conversion_value,
        ctr=ctr,
        cpc=cpc,
        cpm=cpm,
        cpa=cpa,
        roas=roas,
        frequency=frequency,
        click_to_conversion_rate=click_to_conversion_rate,
        wow_spend_delta=wow_spend_delta,
        wow_ctr_delta=wow_ctr_delta,
        wow_roas_delta=wow_roas_delta,
        wow_cpa_delta=wow_cpa_delta,
        daily_points=daily_points if daily_points is not None else make_daily_points(30),
    )


def make_snapshot(
    account: AccountAuditMetrics | None = None,
    campaigns: list[CampaignAuditMetrics] | None = None,
    ad_sets: list[AdSetAuditMetrics] | None = None,
    data_mode: str = "daily_breakdown",
    ad_account_id: str = "act_test",
) -> AccountAuditSnapshot:
    campaigns = campaigns or [make_campaign()]
    ad_sets = ad_sets or [make_adset()]
    return AccountAuditSnapshot(
        ad_account_id=ad_account_id,
        analysis_start=_BASE_DATE,
        analysis_end=_BASE_DATE + timedelta(days=29),
        data_mode=data_mode,
        limitations=[],
        account=account or make_account(),
        campaigns=campaigns,
        ad_sets=ad_sets,
        campaign_count=len(campaigns),
        ad_set_count=len(ad_sets),
        ad_count=len(ad_sets) * 3,
    )


# ---------------------------------------------------------------------------
# Named scenario snapshots
# ---------------------------------------------------------------------------

def healthy_snapshot() -> AccountAuditSnapshot:
    """Healthy account — well-performing metrics. Most rules should NOT fire."""
    account = make_account(
        total_spend=5000.0, ctr=3.5, roas=4.0, frequency=1.8, cpa=15.0,
        total_conversions=300, total_conversion_value=20000.0,
        click_to_conversion_rate=6.0,
    )
    campaigns = [
        make_campaign(
            campaign_id="cmp_1", total_spend=2500.0, ctr=3.5, roas=4.0,
            frequency=1.8, cpa=15.0, spend_share=0.5, total_conversions=150,
            total_conversion_value=10000.0, total_impressions=80_000,
        ),
        make_campaign(
            campaign_id="cmp_2", total_spend=2500.0, ctr=3.3, roas=3.8,
            frequency=2.0, cpa=16.0, spend_share=0.5, total_conversions=150,
            total_conversion_value=9500.0, total_impressions=80_000,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)


def low_ctr_snapshot() -> AccountAuditSnapshot:
    """One campaign with critically low CTR (0.3%) and one with warning CTR (0.8%)."""
    account = make_account(total_spend=2000.0, ctr=0.55)
    campaigns = [
        make_campaign(
            campaign_id="cmp_critical", campaign_name="Critical CTR",
            total_spend=1000.0, total_impressions=50_000,
            ctr=0.3, roas=1.5, spend_share=0.5,
        ),
        make_campaign(
            campaign_id="cmp_warning", campaign_name="Warning CTR",
            total_spend=1000.0, total_impressions=50_000,
            ctr=0.8, roas=2.0, spend_share=0.5,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)


def high_cpa_snapshot() -> AccountAuditSnapshot:
    """Normal campaign dominates conversions; high-CPA campaign has CPA ~4× the computed average.

    Rule computes account_avg_cpa = total_spend / total_conversions across all campaigns
    with conversions > 0. With cmp_normal contributing 1000/50=20 and cmp_high_cpa
    contributing 300/3=100, the account avg ≈ 1300/53 ≈ 24.5. 100 > 24.5*2.5 → CRITICAL.
    """
    account = make_account(total_spend=1300.0, cpa=24.5, roas=2.5)
    campaigns = [
        make_campaign(
            campaign_id="cmp_normal", total_spend=1000.0,
            cpa=20.0, total_conversions=50, roas=2.5, spend_share=0.77,
        ),
        make_campaign(
            campaign_id="cmp_high_cpa", campaign_name="High CPA",
            total_spend=300.0, cpa=100.0, total_conversions=3,
            roas=1.5, spend_share=0.23,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)


def fatigued_snapshot() -> AccountAuditSnapshot:
    """
    Campaign with high frequency (6.0) and a sharply declining CTR trend
    across 28 daily points (from 2.5% down to 0.8%).
    """
    account = make_account(total_spend=3000.0, frequency=5.5)
    fatigued_campaign = make_campaign(
        campaign_id="cmp_fatigued", campaign_name="Fatigued Campaign",
        total_spend=2000.0, frequency=6.0, ctr=1.2, total_impressions=60_000,
        wow_ctr_delta=-0.3, spend_share=0.67,
        daily_points=make_declining_ctr_points(28, start_ctr=2.5, end_ctr=0.8),
    )
    return make_snapshot(account=account, campaigns=[fatigued_campaign])


def budget_imbalanced_snapshot() -> AccountAuditSnapshot:
    """
    One campaign dominates with 75% of spend and a ROAS below account average.
    Another campaign is a winner with high ROAS and underfunded.
    """
    account = make_account(total_spend=4000.0, roas=2.5)
    campaigns = [
        make_campaign(
            campaign_id="cmp_dominant", campaign_name="Dominant Spend",
            total_spend=3000.0, roas=1.2, spend_share=0.75,
            total_conversions=30, total_conversion_value=3600.0,
        ),
        make_campaign(
            campaign_id="cmp_winner", campaign_name="Underfunded Winner",
            total_spend=100.0, roas=5.0, spend_share=0.025,
            total_conversions=30, total_conversion_value=500.0,
        ),
        make_campaign(
            campaign_id="cmp_loser", campaign_name="Low ROAS Loser",
            total_spend=900.0, roas=0.6, spend_share=0.225,
            total_conversions=10, total_conversion_value=540.0,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)


def aggregate_only_snapshot() -> AccountAuditSnapshot:
    """
    Aggregate-only export (no daily breakdowns).
    CTR is low and there are 4+ campaigns so aggregate rules fire.
    """
    account = make_account(
        total_spend=3000.0, ctr=0.4, cpm=30.0, daily_points=[],
    )
    campaigns = [
        make_campaign(
            campaign_id=f"cmp_{i}", campaign_name=f"Campaign {i}",
            total_spend=750.0, ctr=0.4 if i < 2 else 0.45,
            cpm=35.0 if i < 2 else 25.0, spend_share=0.25,
            daily_points=[],
        )
        for i in range(4)
    ]
    return make_snapshot(
        account=account, campaigns=campaigns,
        data_mode="period_aggregate",
    )


def weak_cvr_snapshot() -> AccountAuditSnapshot:
    """Campaigns with plenty of clicks but very low conversion rates.

    cmp_critical: 400 clicks, 0 conversions → CVR = 0% (< 0.5 critical)
    cmp_warning: 500 clicks, 6 conversions → CVR = 1.2% (< 1.5 warning)
    """
    account = make_account(
        total_spend=2500.0,
        total_clicks=900,
        total_conversions=6,
        click_to_conversion_rate=0.67,
    )
    campaigns = [
        make_campaign(
            campaign_id="cmp_zero_cvr",
            campaign_name="Zero CVR Campaign",
            total_spend=1500.0,
            total_clicks=400,
            total_conversions=0,
            total_impressions=40_000,
            click_to_conversion_rate=0.0,
            cpa=0.0,
            roas=0.0,
            total_conversion_value=0.0,
            spend_share=0.6,
        ),
        make_campaign(
            campaign_id="cmp_low_cvr",
            campaign_name="Low CVR Campaign",
            total_spend=1000.0,
            total_clicks=500,
            total_conversions=6,
            total_impressions=30_000,
            click_to_conversion_rate=1.2,
            cpa=166.7,
            roas=1.2,
            total_conversion_value=1200.0,
            spend_share=0.4,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)


def uneven_spend_snapshot() -> AccountAuditSnapshot:
    """Campaign with highly erratic daily spend — high CV indicating pacing issues."""
    from datetime import timedelta

    # Alternate between very low and very high spend days
    uneven_points = [
        DailyMetricPoint(
            date=_BASE_DATE + timedelta(days=i),
            spend=10.0 if i % 2 == 0 else 200.0,
            impressions=2000 if i % 2 == 0 else 20000,
            clicks=40 if i % 2 == 0 else 400,
            conversions=2 if i % 2 == 0 else 10,
            conversion_value=60.0 if i % 2 == 0 else 300.0,
            ctr=2.0,
            cpc=0.5,
            cpm=10.0,
            frequency=2.0,
            roas=3.0,
            cpa=10.0,
        )
        for i in range(28)
    ]
    account = make_account(total_spend=2940.0)
    campaign = make_campaign(
        campaign_id="cmp_uneven",
        campaign_name="Erratic Pacing Campaign",
        total_spend=2940.0,
        spend_share=1.0,
        daily_points=uneven_points,
    )
    return make_snapshot(account=account, campaigns=[campaign])


def broken_funnel_snapshot() -> AccountAuditSnapshot:
    """
    Campaigns with high clicks but zero conversions — broken conversion funnel.
    Also negative ROAS on one campaign.
    """
    account = make_account(
        total_spend=2000.0, total_clicks=4000, total_conversions=0,
        click_to_conversion_rate=0.0, cpa=0.0,
        total_conversion_value=0.0, roas=0.0,
    )
    campaigns = [
        make_campaign(
            campaign_id="cmp_no_conv", campaign_name="No Conversions",
            total_spend=1200.0, total_clicks=2400, total_conversions=0,
            click_to_conversion_rate=0.0, cpa=0.0, roas=0.0,
            total_conversion_value=0.0, spend_share=0.6,
            total_impressions=50_000,
        ),
        make_campaign(
            campaign_id="cmp_neg_roas", campaign_name="Negative ROAS",
            total_spend=800.0, total_clicks=1600, total_conversions=5,
            total_conversion_value=600.0,  # less than spend → ROAS < 1
            cpa=160.0, roas=0.75, click_to_conversion_rate=0.3,
            spend_share=0.4, total_impressions=30_000,
        ),
    ]
    return make_snapshot(account=account, campaigns=campaigns)
