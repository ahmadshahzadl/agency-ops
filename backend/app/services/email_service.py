"""Outgoing email via SMTP. Fire-and-forget: sends run on a daemon thread and
failures are logged, never raised into the request. Disabled entirely when
SMTP_HOST is unset, so local dev and tests need no mail server."""
import logging
import smtplib
import threading
import time
from email.message import EmailMessage
from app.config import get_settings
from app.services import email_template

logger = logging.getLogger("fuorix.email")

settings = get_settings()


def email_enabled() -> bool:
    return bool(settings.smtp_host)


def _build_html(
    title: str,
    body_html: str,
    cta_label: str | None = None,
    cta_url: str | None = None,
    preheader: str | None = None,
    note: str | None = None,
) -> str:
    """Wrap ``body_html`` in the branded shell. Signature kept so every existing caller
    (letters, invoices, quotes, agreements, bookings, password reset) is upgraded at once."""
    return email_template.render(title, body_html, cta_label, cta_url, preheader, note)


def _send(to: str, subject: str, html: str, text: str, attachments: list[tuple] | None = None) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    for att in attachments or []:
        filename, content = att[0], att[1]
        maintype, subtype = (att[2], att[3]) if len(att) >= 4 else ("application", "pdf")
        if subtype == "calendar":
            # RFC 5545: calendar clients look for method=REQUEST/CANCEL on the part.
            method = "CANCEL" if b"METHOD:CANCEL" in content else "REQUEST"
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename, params={"method": method})
        else:
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
    # Transient SMTP hiccups (relay busy, TLS reset) are common; retry a few times before giving up.
    delays = (0, 3, 10)
    for attempt, delay in enumerate(delays, start=1):
        if delay:
            time.sleep(delay)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_tls:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            logger.info("email sent to=%s subject=%s attempt=%d", to, subject, attempt)
            return
        except Exception:
            if attempt == len(delays):
                logger.exception("email send failed to=%s subject=%s after %d attempts", to, subject, attempt)
            else:
                logger.warning("email send attempt %d failed to=%s; retrying", attempt, to, exc_info=True)


def send_email(to: str, subject: str, html: str, text: str, attachments: list[tuple] | None = None) -> None:
    """Queue an email on a background thread. No-op when email is disabled.

    ``attachments`` items are ``(filename, bytes)`` for PDFs or ``(filename, bytes, maintype, subtype)``.
    """
    if not email_enabled() or not to:
        return
    threading.Thread(target=_send, args=(to, subject, html, text, attachments), daemon=True).start()


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
