"""Mock Meta API responses for local development without real credentials.

Activated when META_APP_ID is set to 'mock' in .env.
All data here is fabricated and clearly labelled as mock.
"""

import random
from datetime import date, timedelta


MOCK_TOKEN_DATA = {
    "access_token": "mock_long_lived_token_abc123",
    "expires_in": 5184000,
    "meta_user_id": "10000000000001",
    "meta_user_name": "Test Advertiser",
}


MOCK_AD_ACCOUNTS = [
    {
        "account_id": "act_111111111",
        "name": "Main Brand - US",
        "currency": "USD",
        "timezone_name": "America/New_York",
        "business_name": "Acme Inc.",
        "account_status": 1,
    },
    {
        "account_id": "act_222222222",
        "name": "EU Campaigns",
        "currency": "EUR",
        "timezone_name": "Europe/Berlin",
        "business_name": "Acme Inc.",
        "account_status": 1,
    },
]


def generate_mock_sync_payload() -> dict:
    random.seed(42)
    today = date.today()

    campaigns = [
        {"id": "camp_001", "name": "Brand Awareness US", "status": "ACTIVE", "objective": "BRAND_AWARENESS", "buying_type": "AUCTION", "daily_budget": "5000", "lifetime_budget": None, "created_time": "2025-11-01T10:00:00+00:00", "updated_time": "2026-03-01T12:00:00+00:00"},
        {"id": "camp_002", "name": "Lead Gen Webinar", "status": "ACTIVE", "objective": "LEAD_GENERATION", "buying_type": "AUCTION", "daily_budget": "3000", "lifetime_budget": None, "created_time": "2025-12-10T08:00:00+00:00", "updated_time": "2026-03-05T09:00:00+00:00"},
    ]

    ad_sets = [
        {"id": "as_001", "campaign_id": "camp_001", "name": "Broad 25-44", "status": "ACTIVE", "optimization_goal": "REACH", "billing_event": "IMPRESSIONS", "bid_strategy": "LOWEST_COST_WITHOUT_CAP", "daily_budget": "2500", "lifetime_budget": None, "targeting": {"age_min": 25, "age_max": 44, "geo_locations": {"countries": ["US"]}}, "created_time": "2025-11-01T10:30:00+00:00", "updated_time": "2026-03-01T12:00:00+00:00"},
        {"id": "as_002", "campaign_id": "camp_002", "name": "Interest Marketers", "status": "ACTIVE", "optimization_goal": "LEAD_GENERATION", "billing_event": "IMPRESSIONS", "bid_strategy": "LOWEST_COST_WITH_BID_CAP", "daily_budget": "3000", "lifetime_budget": None, "targeting": {"publisher_platforms": ["facebook", "instagram"]}, "created_time": "2025-12-10T08:30:00+00:00", "updated_time": "2026-03-05T09:00:00+00:00"},
    ]

    creatives = [
        {"id": "cr_001", "name": "Hero Image", "title": "Scale smarter", "body": "Audit your Meta account.", "object_type": "IMAGE", "thumbnail_url": "https://example.com/thumb1.jpg", "image_url": "https://example.com/img1.jpg", "effective_object_story_id": "story_001", "object_story_spec": {"page_id": "1"}, "asset_feed_spec": None},
        {"id": "cr_002", "name": "Lead Form", "title": "Register now", "body": "Join the webinar.", "object_type": "VIDEO", "thumbnail_url": "https://example.com/thumb2.jpg", "image_url": None, "effective_object_story_id": "story_002", "object_story_spec": {"page_id": "2"}, "asset_feed_spec": None},
    ]

    ads = [
        {"id": "ad_001", "adset_id": "as_001", "name": "Hero Ad", "status": "ACTIVE", "creative": {"id": "cr_001"}, "created_time": "2025-11-01T11:00:00+00:00", "updated_time": "2026-03-01T12:00:00+00:00"},
        {"id": "ad_002", "adset_id": "as_002", "name": "Lead Ad", "status": "ACTIVE", "creative": {"id": "cr_002"}, "created_time": "2025-12-10T09:00:00+00:00", "updated_time": "2026-03-05T09:00:00+00:00"},
    ]

    def metric_row(entity_key: str, entity_id: str, base_spend: float, day_offset: int) -> dict:
        spend = round(base_spend * random.uniform(0.75, 1.35), 2)
        impressions = int(spend * random.uniform(90, 180))
        clicks = max(1, int(impressions * random.uniform(0.01, 0.03)))
        reach = max(1, int(impressions * random.uniform(0.6, 0.92)))
        conversions = int(clicks * random.uniform(0.02, 0.1))
        conv_value = round(conversions * random.uniform(20, 120), 2)
        d = today - timedelta(days=day_offset)
        return {
            entity_key: entity_id,
            "date_start": d.isoformat(),
            "impressions": str(impressions),
            "clicks": str(clicks),
            "spend": str(spend),
            "reach": str(reach),
            "ctr": str(round(clicks / impressions * 100, 4)),
            "cpc": str(round(spend / clicks, 2)),
            "cpm": str(round(spend / impressions * 1000, 2)),
            "frequency": str(round(impressions / reach, 2)),
            "actions": [{"action_type": "purchase", "value": str(conversions)}],
            "action_values": [{"action_type": "purchase", "value": str(conv_value)}],
            "purchase_roas": [{"value": str(round(conv_value / spend, 4) if spend else 0)}],
        }

    insights_account = []
    insights_campaign = []
    insights_adset = []
    insights_ad = []

    for day in range(30):
        insights_account.append(metric_row("account_id", "act_111111111", 120.0, day))
        insights_campaign.append(metric_row("campaign_id", "camp_001", 70.0, day))
        insights_campaign.append(metric_row("campaign_id", "camp_002", 50.0, day))
        insights_adset.append(metric_row("adset_id", "as_001", 70.0, day))
        insights_adset.append(metric_row("adset_id", "as_002", 50.0, day))
        insights_ad.append(metric_row("ad_id", "ad_001", 70.0, day))
        insights_ad.append(metric_row("ad_id", "ad_002", 50.0, day))

    return {
        "campaigns": campaigns,
        "ad_sets": ad_sets,
        "creatives": creatives,
        "ads": ads,
        "insights_account": insights_account,
        "insights_campaign": insights_campaign,
        "insights_adset": insights_adset,
        "insights_ad": insights_ad,
    }
