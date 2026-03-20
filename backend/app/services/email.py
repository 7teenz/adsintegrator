import smtplib
from email.mime.text import MIMEText

from app.config import get_settings

settings = get_settings()


class EmailDeliveryError(RuntimeError):
    pass


def build_verification_url(token: str) -> str:
    return f"{settings.frontend_app_url}/verify-email?token={token}"


def build_reset_url(token: str) -> str:
    return f"{settings.frontend_app_url}/reset-password?token={token}"


def send_verification_email(to_email: str, token: str) -> None:
    verify_url = build_verification_url(token)
    body = f"Click to verify your Meta Ads Audit account: {verify_url}"
    _send_email(to_email, "Verify your Meta Ads Audit account", body)


def send_reset_email(to_email: str, token: str) -> None:
    reset_url = build_reset_url(token)
    body = f"Click to reset your Meta Ads Audit password: {reset_url}"
    _send_email(to_email, "Reset your Meta Ads Audit password", body)


def _send_email(to_email: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception as exc:
        raise EmailDeliveryError(str(exc)) from exc
