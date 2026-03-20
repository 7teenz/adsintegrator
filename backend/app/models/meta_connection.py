import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetaConnection(Base):
    __tablename__ = "meta_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    meta_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    meta_user_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_state_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    oauth_state_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    ad_accounts: Mapped[list["MetaAdAccount"]] = relationship(
        "MetaAdAccount", back_populates="connection", cascade="all, delete-orphan"
    )


class MetaAdAccount(Base):
    __tablename__ = "meta_ad_accounts"
    __table_args__ = (UniqueConstraint("connection_id", "account_id", name="uq_meta_ad_accounts_connection_account"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meta_connections.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[str] = mapped_column(String(64), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    business_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_status: Mapped[int | None] = mapped_column(nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    connection: Mapped["MetaConnection"] = relationship(
        "MetaConnection", back_populates="ad_accounts"
    )
