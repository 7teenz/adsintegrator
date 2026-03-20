import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.meta_connection import MetaAdAccount, MetaConnection
from app.services.resilience import with_http_retries_async

settings = get_settings()


class MetaAdsService:
    @staticmethod
    def _graph_api_base() -> str:
        return f"https://graph.facebook.com/{settings.meta_api_version}"

    @classmethod
    async def fetch_ad_accounts(cls, access_token: str) -> list[dict]:
        accounts: list[dict] = []
        url = f"{cls._graph_api_base()}/me/adaccounts"
        params = {
            "access_token": access_token,
            "fields": "account_id,name,currency,timezone_name,business_name,account_status",
            "limit": 100,
        }

        max_pages = settings.meta_pagination_max_pages
        async with httpx.AsyncClient(timeout=float(settings.meta_http_timeout_seconds)) as client:
            page = 0
            while url:
                if page >= max_pages:
                    raise RuntimeError(f"Pagination safety cap reached ({max_pages} pages)")

                async def _request_page():
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response

                response = await with_http_retries_async(_request_page, max_attempts=3)
                payload = response.json()
                accounts.extend(payload.get("data", []))
                url = payload.get("paging", {}).get("next")
                params = {}
                page += 1

        return accounts

    @staticmethod
    def sync_ad_accounts(
        db: Session,
        connection: MetaConnection,
        raw_accounts: list[dict],
        max_accounts: int | None = None,
    ) -> list[MetaAdAccount]:
        existing = {
            account.account_id: account
            for account in db.query(MetaAdAccount)
            .filter(MetaAdAccount.connection_id == connection.id)
            .all()
        }
        selected_account_id = next(
            (account.account_id for account in existing.values() if account.is_selected),
            None,
        )

        result: list[MetaAdAccount] = []
        seen_ids: set[str] = set()
        candidates = raw_accounts[:max_accounts] if max_accounts is not None else raw_accounts

        for raw in candidates:
            account_id = raw.get("account_id")
            if not account_id:
                continue
            seen_ids.add(account_id)

            account = existing.get(account_id)
            if account is None:
                account = MetaAdAccount(connection_id=connection.id, account_id=account_id)
                db.add(account)

            account.account_name = raw.get("name")
            account.currency = raw.get("currency")
            account.timezone = raw.get("timezone_name")
            account.business_name = raw.get("business_name")
            account.account_status = raw.get("account_status")
            account.is_selected = account_id == selected_account_id
            result.append(account)

        for account_id, account in existing.items():
            if account_id not in seen_ids:
                db.delete(account)

        db.commit()
        for account in result:
            db.refresh(account)
        return result

    @staticmethod
    def get_ad_accounts(db: Session, connection_id: str) -> list[MetaAdAccount]:
        return (
            db.query(MetaAdAccount)
            .filter(MetaAdAccount.connection_id == connection_id)
            .order_by(MetaAdAccount.account_name.asc().nullslast(), MetaAdAccount.account_id.asc())
            .all()
        )

    @staticmethod
    def select_ad_account(db: Session, connection_id: str, account_id: str) -> MetaAdAccount | None:
        accounts = db.query(MetaAdAccount).filter(MetaAdAccount.connection_id == connection_id).all()
        selected = None
        for account in accounts:
            account.is_selected = account.account_id == account_id
            if account.is_selected:
                selected = account
        db.commit()
        if selected is not None:
            db.refresh(selected)
        return selected

    @staticmethod
    def get_selected_account(db: Session, connection_id: str) -> MetaAdAccount | None:
        return (
            db.query(MetaAdAccount)
            .filter(
                MetaAdAccount.connection_id == connection_id,
                MetaAdAccount.is_selected.is_(True),
            )
            .first()
        )
