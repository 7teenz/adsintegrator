from pydantic import BaseModel


class ApiError(BaseModel):
    detail: str
    code: str
    request_id: str | None = None
