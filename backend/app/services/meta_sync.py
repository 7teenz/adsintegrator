import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.campaign import Ad, AdSet, Campaign, Creative
from app.models.insights import (
    DailyAccountInsight,
    DailyAdInsight,
    DailyAdSetInsight,
    DailyCampaignInsight,
)
from app.models.meta_connection import MetaAdAccount
from app.models.sync_job import SyncJob, SyncJobLog
from app.services.meta_auth import MetaAuthService
from app.services.resilience import with_http_retries

settings = get_settings()

CAMPAIGN_FIELDS = "id,name,status,objective,buying_type,daily_budget,lifetime_budget,created_time,updated_time"
ADSET_FIELDS = "id,campaign_id,name,status,targeting,optimization_goal,billing_event,bid_strategy,daily_budget,lifetime_budget,created_time,updated_time"
AD_FIELDS = "id,adset_id,name,status,creative{id},created_time,updated_time"
CREATIVE_FIELDS = "id,name,title,body,object_type,thumbnail_url,image_url,effective_object_story_id,object_story_spec,asset_feed_spec"
INSIGHT_FIELDS = "date_start,impressions,clicks,spend,reach,ctr,cpc,cpm,frequency,actions,action_values,purchase_roas"


@dataclass
class SyncWindow:
    since: date
    until: date


class MetaSyncFetchService:
    @staticmethod
    def _graph_api_base() -> str:
        return f"https://graph.facebook.com/{settings.meta_api_version}"

    @staticmethod
    def _paginated_get(access_token: str, url: str, params: dict) -> list[dict]:
        results: list[dict] = []
        request_params = {**params, "access_token": access_token, "limit": params.get("limit", 200)}
        max_pages = settings.meta_pagination_max_pages

        with httpx.Client(timeout=float(settings.meta_http_timeout_seconds)) as client:
            next_url = url
            page = 0
            while next_url:
                if page >= max_pages:
                    raise RuntimeError(f"Pagination safety cap reached ({max_pages} pages)")

                def _request_page():
                    response = client.get(next_url, params=request_params)
                    response.raise_for_status()
                    return response

                response = with_http_retries(_request_page, max_attempts=3)
                payload = response.json()
                results.extend(payload.get("data", []))
                next_url = payload.get("paging", {}).get("next")
                request_params = {}
                page += 1

        return results

    @classmethod
    def fetch_campaigns(cls, access_token: str, meta_account_id: str) -> list[dict]:
        return cls._paginated_get(
            access_token,
            f"{cls._graph_api_base()}/{meta_account_id}/campaigns",
            {"fields": CAMPAIGN_FIELDS},
        )

    @classmethod
    def fetch_ad_sets(cls, access_token: str, meta_account_id: str) -> list[dict]:
        return cls._paginated_get(
            access_token,
            f"{cls._graph_api_base()}/{meta_account_id}/adsets",
            {"fields": ADSET_FIELDS},
        )

    @classmethod
    def fetch_ads(cls, access_token: str, meta_account_id: str) -> list[dict]:
        return cls._paginated_get(
            access_token,
            f"{cls._graph_api_base()}/{meta_account_id}/ads",
            {"fields": AD_FIELDS},
        )

    @classmethod
    def fetch_creatives(cls, access_token: str, meta_account_id: str) -> list[dict]:
        return cls._paginated_get(
            access_token,
            f"{cls._graph_api_base()}/{meta_account_id}/adcreatives",
            {"fields": CREATIVE_FIELDS},
        )

    @classmethod
    def fetch_insights(cls, access_token: str, meta_account_id: str, level: str, window: SyncWindow) -> list[dict]:
        return cls._paginated_get(
            access_token,
            f"{cls._graph_api_base()}/{meta_account_id}/insights",
            {
                "fields": INSIGHT_FIELDS,
                "level": level,
                "time_increment": 1,
                "time_range": json.dumps({"since": window.since.isoformat(), "until": window.until.isoformat()}),
            },
        )


class MetaSyncPersistenceService:
    @staticmethod
    def upsert_campaigns(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        existing = {
            row.meta_campaign_id: row
            for row in db.query(Campaign).filter(Campaign.ad_account_id == ad_account_id).all()
        }
        count = 0
        for raw in rows:
            meta_id = raw.get("id")
            if not meta_id:
                continue
            campaign = existing.get(meta_id)
            if campaign is None:
                campaign = Campaign(ad_account_id=ad_account_id, meta_campaign_id=meta_id, name=raw.get("name") or meta_id)
                db.add(campaign)
            campaign.name = raw.get("name") or campaign.name
            campaign.status = raw.get("status")
            campaign.objective = raw.get("objective")
            campaign.buying_type = raw.get("buying_type")
            campaign.daily_budget = _safe_float(raw.get("daily_budget"))
            campaign.lifetime_budget = _safe_float(raw.get("lifetime_budget"))
            campaign.source_created_time = _safe_datetime(raw.get("created_time"))
            campaign.source_updated_time = _safe_datetime(raw.get("updated_time"))
            campaign.synced_at = datetime.now(timezone.utc)
            count += 1
        db.flush()
        return count

    @staticmethod
    def upsert_ad_sets(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        campaign_map = {
            campaign.meta_campaign_id: campaign.id
            for campaign in db.query(Campaign).filter(Campaign.ad_account_id == ad_account_id).all()
        }
        existing = {
            row.meta_adset_id: row
            for row in db.query(AdSet).filter(AdSet.ad_account_id == ad_account_id).all()
        }
        count = 0
        for raw in rows:
            meta_id = raw.get("id")
            campaign_id = campaign_map.get(raw.get("campaign_id"))
            if not meta_id or not campaign_id:
                continue
            ad_set = existing.get(meta_id)
            if ad_set is None:
                ad_set = AdSet(
                    ad_account_id=ad_account_id,
                    campaign_id=campaign_id,
                    meta_adset_id=meta_id,
                    meta_campaign_id=raw.get("campaign_id") or "",
                    name=raw.get("name") or meta_id,
                )
                db.add(ad_set)
            ad_set.campaign_id = campaign_id
            ad_set.meta_campaign_id = raw.get("campaign_id") or ad_set.meta_campaign_id
            ad_set.name = raw.get("name") or ad_set.name
            ad_set.status = raw.get("status")
            ad_set.targeting_summary = _targeting_summary(raw.get("targeting"))
            ad_set.optimization_goal = raw.get("optimization_goal")
            ad_set.billing_event = raw.get("billing_event")
            ad_set.bid_strategy = raw.get("bid_strategy")
            ad_set.daily_budget = _safe_float(raw.get("daily_budget"))
            ad_set.lifetime_budget = _safe_float(raw.get("lifetime_budget"))
            ad_set.source_created_time = _safe_datetime(raw.get("created_time"))
            ad_set.source_updated_time = _safe_datetime(raw.get("updated_time"))
            ad_set.synced_at = datetime.now(timezone.utc)
            count += 1
        db.flush()
        return count

    @staticmethod
    def upsert_creatives(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        existing = {
            row.meta_creative_id: row
            for row in db.query(Creative).filter(Creative.ad_account_id == ad_account_id).all()
        }
        count = 0
        for raw in rows:
            meta_id = raw.get("id")
            if not meta_id:
                continue
            creative = existing.get(meta_id)
            if creative is None:
                creative = Creative(ad_account_id=ad_account_id, meta_creative_id=meta_id)
                db.add(creative)
            creative.name = raw.get("name")
            creative.title = raw.get("title")
            creative.body = raw.get("body")
            creative.object_type = raw.get("object_type")
            creative.thumbnail_url = raw.get("thumbnail_url")
            creative.image_url = raw.get("image_url")
            creative.effective_object_story_id = raw.get("effective_object_story_id")
            creative.object_story_spec_json = _safe_json(raw.get("object_story_spec"))
            creative.asset_feed_spec_json = _safe_json(raw.get("asset_feed_spec"))
            creative.synced_at = datetime.now(timezone.utc)
            count += 1
        db.flush()
        return count

    @staticmethod
    def upsert_ads(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        ad_set_map = {
            row.meta_adset_id: row.id
            for row in db.query(AdSet).filter(AdSet.ad_account_id == ad_account_id).all()
        }
        creative_map = {
            row.meta_creative_id: row.id
            for row in db.query(Creative).filter(Creative.ad_account_id == ad_account_id).all()
        }
        existing = {
            row.meta_ad_id: row
            for row in db.query(Ad).filter(Ad.ad_account_id == ad_account_id).all()
        }
        count = 0
        for raw in rows:
            meta_id = raw.get("id")
            ad_set_id = ad_set_map.get(raw.get("adset_id"))
            if not meta_id or not ad_set_id:
                continue
            creative = raw.get("creative") if isinstance(raw.get("creative"), dict) else {}
            meta_creative_id = creative.get("id")
            ad = existing.get(meta_id)
            if ad is None:
                ad = Ad(
                    ad_account_id=ad_account_id,
                    ad_set_id=ad_set_id,
                    meta_ad_id=meta_id,
                    meta_adset_id=raw.get("adset_id") or "",
                    name=raw.get("name") or meta_id,
                )
                db.add(ad)
            ad.ad_set_id = ad_set_id
            ad.meta_adset_id = raw.get("adset_id") or ad.meta_adset_id
            ad.creative_pk = creative_map.get(meta_creative_id) if meta_creative_id else None
            ad.meta_creative_id = meta_creative_id
            ad.name = raw.get("name") or ad.name
            ad.status = raw.get("status")
            ad.source_created_time = _safe_datetime(raw.get("created_time"))
            ad.source_updated_time = _safe_datetime(raw.get("updated_time"))
            ad.synced_at = datetime.now(timezone.utc)
            count += 1
        db.flush()
        return count

    @staticmethod
    def upsert_account_insights(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        existing = {
            row.date: row
            for row in db.query(DailyAccountInsight).filter(DailyAccountInsight.ad_account_id == ad_account_id).all()
        }
        return _upsert_insights(db, DailyAccountInsight, existing, rows, {"ad_account_id": ad_account_id})

    @staticmethod
    def upsert_campaign_insights(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        campaign_map = {
            row.meta_campaign_id: row.id
            for row in db.query(Campaign).filter(Campaign.ad_account_id == ad_account_id).all()
        }
        existing = {
            (row.campaign_id, row.date): row
            for row in db.query(DailyCampaignInsight).filter(DailyCampaignInsight.ad_account_id == ad_account_id).all()
        }
        return _upsert_entity_insights(
            db,
            DailyCampaignInsight,
            rows,
            existing,
            campaign_map,
            "campaign_id",
            {"ad_account_id": ad_account_id},
        )

    @staticmethod
    def upsert_adset_insights(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        ad_set_map = {
            row.meta_adset_id: row.id
            for row in db.query(AdSet).filter(AdSet.ad_account_id == ad_account_id).all()
        }
        existing = {
            (row.ad_set_id, row.date): row
            for row in db.query(DailyAdSetInsight).filter(DailyAdSetInsight.ad_account_id == ad_account_id).all()
        }
        return _upsert_entity_insights(
            db,
            DailyAdSetInsight,
            rows,
            existing,
            ad_set_map,
            "adset_id",
            {"ad_account_id": ad_account_id},
        )

    @staticmethod
    def upsert_ad_insights(db: Session, ad_account_id: str, rows: list[dict]) -> int:
        ad_map = {
            row.meta_ad_id: row.id
            for row in db.query(Ad).filter(Ad.ad_account_id == ad_account_id).all()
        }
        existing = {
            (row.ad_id, row.date): row
            for row in db.query(DailyAdInsight).filter(DailyAdInsight.ad_account_id == ad_account_id).all()
        }
        return _upsert_entity_insights(
            db,
            DailyAdInsight,
            rows,
            existing,
            ad_map,
            "ad_id",
            {"ad_account_id": ad_account_id},
        )


class MetaSyncOrchestrator:
    @staticmethod
    def determine_window(sync_type: str, latest_success: SyncJob | None) -> SyncWindow:
        until = date.today() - timedelta(days=1)
        if sync_type == "initial" or latest_success is None or latest_success.completed_at is None:
            since = until - timedelta(days=settings.meta_initial_sync_lookback_days - 1)
        else:
            fallback = until - timedelta(days=settings.meta_incremental_sync_lookback_days - 1)
            cursor = latest_success.completed_at.date() - timedelta(days=1)
            since = max(cursor, fallback)
        return SyncWindow(since=since, until=until)

    @classmethod
    def run(cls, db: Session, job: SyncJob, mock_payload: dict | None = None) -> None:
        ad_account = db.query(MetaAdAccount).filter(MetaAdAccount.id == job.ad_account_id).first()
        if ad_account is None:
            raise ValueError("Selected ad account was not found")

        latest_success = (
            db.query(SyncJob)
            .filter(
                SyncJob.ad_account_id == ad_account.id,
                SyncJob.status == "completed",
                SyncJob.id != job.id,
            )
            .order_by(SyncJob.completed_at.desc())
            .first()
        )
        window = cls.determine_window(job.sync_type, latest_success)
        job.window_start = datetime.combine(window.since, datetime.min.time())
        job.window_end = datetime.combine(window.until, datetime.max.time())
        job.last_successful_cursor = latest_success.completed_at if latest_success else None
        db.commit()

        if mock_payload is not None:
            payload = mock_payload
        else:
            connection = MetaAuthService.get_connection(db, job.user_id)
            if connection is None:
                raise ValueError("Meta connection was not found")
            access_token = MetaAuthService.get_access_token(connection)
            payload = cls._fetch_remote_payload(access_token, ad_account.account_id, window)

        steps = [
            ("campaigns", 10, lambda: MetaSyncPersistenceService.upsert_campaigns(db, ad_account.id, payload.get("campaigns", []))),
            ("ad sets", 20, lambda: MetaSyncPersistenceService.upsert_ad_sets(db, ad_account.id, payload.get("ad_sets", []))),
            ("creatives", 32, lambda: MetaSyncPersistenceService.upsert_creatives(db, ad_account.id, payload.get("creatives", []))),
            ("ads", 42, lambda: MetaSyncPersistenceService.upsert_ads(db, ad_account.id, payload.get("ads", []))),
            ("account insights", 58, lambda: MetaSyncPersistenceService.upsert_account_insights(db, ad_account.id, payload.get("insights_account", []))),
            ("campaign insights", 72, lambda: MetaSyncPersistenceService.upsert_campaign_insights(db, ad_account.id, payload.get("insights_campaign", []))),
            ("ad set insights", 86, lambda: MetaSyncPersistenceService.upsert_adset_insights(db, ad_account.id, payload.get("insights_adset", []))),
            ("ad insights", 96, lambda: MetaSyncPersistenceService.upsert_ad_insights(db, ad_account.id, payload.get("insights_ad", []))),
        ]

        count_map = {
            "campaigns": "campaigns_synced",
            "ad sets": "ad_sets_synced",
            "ads": "ads_synced",
            "creatives": "creatives_synced",
            "account insights": "insights_account_synced",
            "campaign insights": "insights_campaign_synced",
            "ad set insights": "insights_adset_synced",
            "ad insights": "insights_ad_synced",
        }

        for label, progress, operation in steps:
            cls.log(db, job, f"Syncing {label}")
            job.current_step = f"Syncing {label}"
            job.progress = progress
            db.commit()
            synced_count = operation()
            setattr(job, count_map[label], synced_count)
            job.progress = min(progress + 8, 99)
            db.commit()

        job.progress = 100
        job.current_step = "Sync complete"
        cls.log(db, job, "Sync completed")
        db.commit()

    @classmethod
    def _fetch_remote_payload(cls, access_token: str, meta_account_id: str, window: SyncWindow) -> dict:
        return {
            "campaigns": MetaSyncFetchService.fetch_campaigns(access_token, meta_account_id),
            "ad_sets": MetaSyncFetchService.fetch_ad_sets(access_token, meta_account_id),
            "creatives": MetaSyncFetchService.fetch_creatives(access_token, meta_account_id),
            "ads": MetaSyncFetchService.fetch_ads(access_token, meta_account_id),
            "insights_account": MetaSyncFetchService.fetch_insights(access_token, meta_account_id, "account", window),
            "insights_campaign": MetaSyncFetchService.fetch_insights(access_token, meta_account_id, "campaign", window),
            "insights_adset": MetaSyncFetchService.fetch_insights(access_token, meta_account_id, "adset", window),
            "insights_ad": MetaSyncFetchService.fetch_insights(access_token, meta_account_id, "ad", window),
        }

    @staticmethod
    def log(db: Session, job: SyncJob, message: str, level: str = "info") -> None:
        db.add(SyncJobLog(sync_job_id=job.id, level=level, message=message))
        db.commit()


def _targeting_summary(value: dict | None) -> str | None:
    if not value:
        return None
    if isinstance(value, dict):
        parts = []
        if value.get("geo_locations"):
            parts.append("geo")
        if value.get("publisher_platforms"):
            parts.append("platforms")
        if value.get("age_min") or value.get("age_max"):
            parts.append(f"ages {value.get('age_min', '?')}-{value.get('age_max', '?')}")
        return ", ".join(parts) if parts else json.dumps(value)
    return str(value)


def _safe_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _safe_json(value) -> str | None:
    if value is None:
        return None
    try:
        return json.dumps(value)
    except TypeError:
        return None


def _metrics_from_raw(raw: dict) -> dict:
    conversions = 0
    conversion_value = 0.0
    roas = 0.0
    for action in raw.get("actions", []) or []:
        action_type = action.get("action_type", "")
        if action_type in {"purchase", "offsite_conversion", "lead", "omni_purchase"}:
            conversions += _safe_int(action.get("value"))
    for action_value in raw.get("action_values", []) or []:
        action_type = action_value.get("action_type", "")
        if action_type in {"purchase", "offsite_conversion", "omni_purchase"}:
            conversion_value += _safe_float(action_value.get("value"))
    purchase_roas = raw.get("purchase_roas") or []
    if purchase_roas:
        first = purchase_roas[0]
        roas = _safe_float(first.get("value") if isinstance(first, dict) else first)
    elif _safe_float(raw.get("spend")) > 0:
        roas = conversion_value / _safe_float(raw.get("spend"))
    return {
        "impressions": _safe_int(raw.get("impressions")),
        "clicks": _safe_int(raw.get("clicks")),
        "spend": _safe_float(raw.get("spend")),
        "reach": _safe_int(raw.get("reach")),
        "ctr": _safe_float(raw.get("ctr")),
        "cpc": _safe_float(raw.get("cpc")),
        "cpm": _safe_float(raw.get("cpm")),
        "frequency": _safe_float(raw.get("frequency")),
        "conversions": conversions,
        "conversion_value": conversion_value,
        "roas": roas,
    }


def _upsert_insights(db: Session, model, existing_map: dict, rows: list[dict], base_kwargs: dict) -> int:
    count = 0
    for raw in rows:
        insight_date = _parse_date(raw.get("date_start"))
        if insight_date is None:
            continue
        row = existing_map.get(insight_date)
        if row is None:
            row = model(date=insight_date, **base_kwargs)
            db.add(row)
        for key, value in _metrics_from_raw(raw).items():
            setattr(row, key, value)
        row.synced_at = datetime.now(timezone.utc)
        count += 1
    db.flush()
    return count


def _upsert_entity_insights(db: Session, model, rows: list[dict], existing_map: dict, entity_map: dict, raw_id_key: str, base_kwargs: dict) -> int:
    count = 0
    entity_column = {
        "campaign_id": "campaign_id",
        "adset_id": "ad_set_id",
        "ad_id": "ad_id",
    }[raw_id_key]
    for raw in rows:
        insight_date = _parse_date(raw.get("date_start"))
        entity_local_id = entity_map.get(raw.get(raw_id_key))
        if insight_date is None or entity_local_id is None:
            continue
        row = existing_map.get((entity_local_id, insight_date))
        if row is None:
            row = model(date=insight_date, **base_kwargs)
            setattr(row, entity_column, entity_local_id)
            db.add(row)
        for key, value in _metrics_from_raw(raw).items():
            setattr(row, key, value)
        row.synced_at = datetime.now(timezone.utc)
        count += 1
    db.flush()
    return count


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
