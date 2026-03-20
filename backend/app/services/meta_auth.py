import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.meta_connection import MetaConnection
from app.services.crypto import decrypt_token, encrypt_token
from app.services.resilience import with_http_retries_async

settings = get_settings()


class MetaAuthService:
    @staticmethod
    def _graph_api_base() -> str:
        return f"https://graph.facebook.com/{settings.meta_api_version}"

    @staticmethod
    def _dialog_base() -> str:
        return f"https://www.facebook.com/{settings.meta_api_version}/dialog/oauth"

    @staticmethod
    def _hash_state(state: str) -> str:
        return hashlib.sha256(state.encode()).hexdigest()

    @classmethod
    def _get_or_create_connection(cls, db: Session, user_id: str) -> MetaConnection:
        connection = db.query(MetaConnection).filter(MetaConnection.user_id == user_id).first()
        if connection is None:
            connection = MetaConnection(user_id=user_id)
            db.add(connection)
            db.flush()
        return connection

    @classmethod
    def create_authorization_request(cls, db: Session, user_id: str, redirect_uri: str) -> str:
        if settings.meta_app_id != "mock" and (not settings.meta_app_id or not settings.meta_app_secret):
            raise ValueError("Meta app credentials are not configured")

        state = secrets.token_urlsafe(32)
        connection = cls._get_or_create_connection(db, user_id)
        connection.oauth_state_hash = cls._hash_state(state)
        connection.oauth_state_expires_at = datetime.utcnow() + timedelta(minutes=settings.meta_state_ttl_minutes)
        connection.updated_at = datetime.utcnow()
        db.commit()

        params = {
            "client_id": settings.meta_app_id,
            "redirect_uri": redirect_uri,
            "scope": settings.meta_oauth_scopes,
            "response_type": "code",
            "state": state,
        }
        return f"{cls._dialog_base()}?{urlencode(params)}"

    @classmethod
    def validate_state(cls, db: Session, user_id: str, state: str) -> MetaConnection:
        connection = db.query(MetaConnection).filter(MetaConnection.user_id == user_id).first()
        if connection is None or connection.oauth_state_hash is None or connection.oauth_state_expires_at is None:
            raise ValueError("Missing OAuth session. Start the Meta connection flow again.")
        if connection.oauth_state_expires_at < datetime.utcnow():
            raise ValueError("OAuth session expired. Start the Meta connection flow again.")
        if connection.oauth_state_hash != cls._hash_state(state):
            raise ValueError("Invalid OAuth state. Start the Meta connection flow again.")
        return connection

    @classmethod
    async def exchange_code(cls, code: str, redirect_uri: str) -> dict:
        timeout = float(settings.meta_http_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async def _exchange_short():
                resp = await client.get(
                    f"{cls._graph_api_base()}/oauth/access_token",
                    params={
                        "client_id": settings.meta_app_id,
                        "client_secret": settings.meta_app_secret,
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                )
                resp.raise_for_status()
                return resp.json()

            short_data = await with_http_retries_async(_exchange_short, max_attempts=3)

            async def _exchange_long():
                resp = await client.get(
                    f"{cls._graph_api_base()}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": settings.meta_app_id,
                        "client_secret": settings.meta_app_secret,
                        "fb_exchange_token": short_data["access_token"],
                    },
                )
                resp.raise_for_status()
                return resp.json()

            token_data = await with_http_retries_async(_exchange_long, max_attempts=3)

            async def _fetch_me():
                resp = await client.get(
                    f"{cls._graph_api_base()}/me",
                    params={
                        "access_token": token_data["access_token"],
                        "fields": "id,name",
                    },
                )
                resp.raise_for_status()
                return resp.json()

            me = await with_http_retries_async(_fetch_me, max_attempts=3)

        return {
            "access_token": token_data["access_token"],
            "expires_in": token_data.get("expires_in"),
            "meta_user_id": me["id"],
            "meta_user_name": me.get("name"),
            "scopes": settings.meta_oauth_scopes,
        }

    @classmethod
    def save_connection(cls, db: Session, user_id: str, token_data: dict) -> MetaConnection:
        connection = cls._get_or_create_connection(db, user_id)
        expires_at = None
        expires_in = token_data.get("expires_in")
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        connection.meta_user_id = token_data["meta_user_id"]
        connection.meta_user_name = token_data.get("meta_user_name")
        connection.encrypted_access_token = encrypt_token(token_data["access_token"])
        connection.token_expires_at = expires_at
        connection.scopes = token_data.get("scopes", settings.meta_oauth_scopes)
        connection.oauth_state_hash = None
        connection.oauth_state_expires_at = None
        connection.updated_at = datetime.utcnow()

        db.add(connection)
        db.commit()
        db.refresh(connection)
        return connection

    @staticmethod
    def get_connection(db: Session, user_id: str) -> MetaConnection | None:
        return db.query(MetaConnection).filter(MetaConnection.user_id == user_id).first()

    @staticmethod
    def is_connected(connection: MetaConnection | None) -> bool:
        return bool(connection and connection.encrypted_access_token)

    @staticmethod
    def get_access_token(connection: MetaConnection) -> str:
        if not connection.encrypted_access_token:
            raise ValueError("Meta connection is not complete")
        return decrypt_token(connection.encrypted_access_token)

    @staticmethod
    def delete_connection(db: Session, user_id: str) -> bool:
        connection = db.query(MetaConnection).filter(MetaConnection.user_id == user_id).first()
        if connection is None:
            return False
        db.delete(connection)
        db.commit()
        return True
