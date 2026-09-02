"""Outgoing email via SMTP. Fire-and-forget: sends run on a daemon thread and
failures are logged, never raised into the request. Disabled entirely when
SMTP_HOST is unset, so local dev and tests need no mail server."""
import logging
import smtplib
import threading
from email.message import EmailMessage
from app.config import get_settings

logger = logging.getLogger("fuorix.email")

settings = get_settings()


def email_enabled() -> bool:
    return bool(settings.smtp_host)


def _build_html(title: str, body_html: str, cta_label: str | None = None, cta_url: str | None = None) -> str:
    button = ""
    if cta_label and cta_url:
        button = (
            f'<p style="margin:28px 0;"><a href="{cta_url}" '
            f'style="background:#01184e;color:#ffffff;text-decoration:none;padding:12px 24px;'
            f'border-radius:10px;font-weight:600;display:inline-block;">{cta_label}</a></p>'
        )
    return f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;background:#f4f5f7;padding:32px 16px;">
  <div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:14px;overflow:hidden;">
    <div style="background:#01184e;padding:20px 28px;">
      <span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:0.5px;">{settings.app_name.replace(' API', '')}</span>
    </div>
    <div style="padding:28px;color:#1f2937;font-size:15px;line-height:1.6;">
      <h2 style="margin:0 0 12px;font-size:19px;color:#111827;">{title}</h2>
      {body_html}
      {button}
    </div>
    <div style="padding:16px 28px;border-top:1px solid #f0f0f0;color:#9ca3af;font-size:12px;">
      This is an automated message — replies are not monitored.
    </div>
  </div>
</div>"""


def _send(to: str, subject: str, html: str, text: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("email sent to=%s subject=%s", to, subject)
    except Exception:
        logger.exception("email send failed to=%s subject=%s", to, subject)


def send_email(to: str, subject: str, html: str, text: str) -> None:
    """Queue an email on a background thread. No-op when email is disabled."""
    if not email_enabled() or not to:
        return
    threading.Thread(target=_send, args=(to, subject, html, text), daemon=True).start()


def send_password_reset(to: str, user_name: str, token: str) -> None:
    url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    title = "Reset your password"
    body = (
        f"<p>Hi {user_name or 'there'},</p>"
        "<p>We received a request to reset your password. The link below is valid for <b>1 hour</b> "
        "and can be used once. If you didn't request this, you can safely ignore this email.</p>"
    )
    text = f"Reset your password (valid 1 hour): {url}\nIf you didn't request this, ignore this email."
    send_email(to, "Reset your password", _build_html(title, body, "Reset password", url), text)


def send_notification(to: str, subject: str, message: str, link_path: str | None = None) -> None:
    url = f"{settings.frontend_url.rstrip('/')}{link_path}" if link_path else None
    body = f"<p>{message}</p>"
    text = message + (f"\n{url}" if url else "")
    send_email(to, subject, _build_html(subject, body, "Open in Fuorix" if url else None, url), text)
