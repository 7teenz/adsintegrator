import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import sentry_sdk
from starlette import status

from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.observability import init_sentry
from app.routes import audit, auth, billing, debug, health, meta, sync

settings = get_settings()
configure_logging("INFO")
init_sentry(settings)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    logger.info(
        "request.started",
        extra={
            "request_id": request_id,
            "code": "REQUEST_STARTED",
            "method": request.method,
            "path": request.url.path,
        },
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request.completed",
        extra={
            "request_id": request_id,
            "user_id": getattr(request.state, "user_id", None),
            "code": "REQUEST_COMPLETED",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    sentry_sdk.capture_exception(exc)
    logger.exception(
        "request.failed",
        extra={
            "request_id": request_id,
            "user_id": getattr(request.state, "user_id", None),
            "code": "INTERNAL_ERROR",
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
            "request_id": request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", None)
    code = "HTTP_ERROR"
    detail = exc.detail
    if isinstance(exc.detail, dict):
        detail = exc.detail.get("detail", "Request failed")
        code = exc.detail.get("code", "HTTP_ERROR")
    if exc.status_code >= 500:
        sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": detail,
            "code": code,
            "request_id": request_id,
        },
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    details = [f"{'.'.join([str(p) for p in item['loc']])}: {item['msg']}" for item in exc.errors()]
    logger.warning(
        "request.validation_failed",
        extra={
            "request_id": request_id,
            "user_id": getattr(request.state, "user_id", None),
            "code": "VALIDATION_ERROR",
            "method": request.method,
            "path": request.url.path,
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "; ".join(details)[:2000] or "Validation failed",
            "code": "VALIDATION_ERROR",
            "request_id": request_id,
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(meta.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
if settings.debug:
    app.include_router(debug.router, prefix="/api")
