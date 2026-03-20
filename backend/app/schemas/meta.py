from datetime import datetime

from pydantic import BaseModel, Field


class MetaAuthURL(BaseModel):
    url: str


class MetaCallbackRequest(BaseModel):
    code: str = Field(min_length=4, max_length=2048)
    state: str = Field(min_length=8, max_length=512)


class MetaConnectionResponse(BaseModel):
    id: str
    meta_user_id: str
    meta_user_name: str | None
    token_expires_at: datetime | None
    scopes: str | None
    created_at: datetime
    has_selected_account: bool = False

    model_config = {"from_attributes": True}


class MetaConnectionStatus(BaseModel):
    connected: bool
    connection: MetaConnectionResponse | None = None


class MetaAdAccountResponse(BaseModel):
    id: str
    account_id: str
    account_name: str | None
    currency: str | None
    timezone: str | None
    business_name: str | None
    account_status: int | None
    is_selected: bool

    model_config = {"from_attributes": True}


class AdAccountSelectRequest(BaseModel):
    account_id: str = Field(min_length=3, max_length=64)
