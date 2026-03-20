from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SyncType = Literal["initial", "incremental"]
SyncStatus = Literal["pending", "running", "retrying", "completed", "failed"]
LogLevel = Literal["debug", "info", "warning", "error", "critical"]


class SyncJobLogResponse(BaseModel):
    id: str
    level: LogLevel | str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncJobResponse(BaseModel):
    id: str
    sync_type: SyncType
    status: SyncStatus
    progress: int = Field(ge=0, le=100)
    current_step: str | None
    celery_task_id: str | None
    campaigns_synced: int = Field(ge=0)
    ad_sets_synced: int = Field(ge=0)
    ads_synced: int = Field(ge=0)
    creatives_synced: int = Field(ge=0)
    insights_account_synced: int = Field(ge=0)
    insights_campaign_synced: int = Field(ge=0)
    insights_adset_synced: int = Field(ge=0)
    insights_ad_synced: int = Field(ge=0)
    error_message: str | None
    window_start: datetime | None
    window_end: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    logs: list[SyncJobLogResponse] = []

    model_config = {"from_attributes": True}


class SyncStartRequest(BaseModel):
    sync_type: SyncType = "initial"


class SyncStartResponse(BaseModel):
    job: SyncJobResponse
    message: str


class SyncDataSummary(BaseModel):
    campaigns: int = Field(ge=0)
    ad_sets: int = Field(ge=0)
    ads: int = Field(ge=0)
    creatives: int = Field(ge=0)
    account_insight_rows: int = Field(ge=0)
    campaign_insight_rows: int = Field(ge=0)
    adset_insight_rows: int = Field(ge=0)
    ad_insight_rows: int = Field(ge=0)
    sync_state: SyncStatus
    last_sync: SyncJobResponse | None


class CsvImportResponse(BaseModel):
    campaigns: int = Field(ge=0)
    ad_sets: int = Field(ge=0)
    ads: int = Field(ge=0)
    insight_rows: int = Field(ge=0)
    date_start: datetime | None = None
    date_end: datetime | None = None
    replaced_existing: bool = False
    report_type: str = "daily_breakdown"
    source_sheet: str | None = None
    warnings: list[str] = []


class ReportImportResponse(CsvImportResponse):
    pass
