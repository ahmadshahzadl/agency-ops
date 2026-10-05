"""Signing-link lifecycle and the acceptance record shared by the public link and the portal.

The acceptance record is the legally meaningful artifact: who signed (typed name, email, title),
when, from which address and browser, and a hash that ties the signature to the exact clause
text. It is printed on the PDF so the executed copy carries its own evidence."""
import hashlib
import json
import logging
import secrets
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Agreement as AgreementModel, Notification as NotificationModel, User as UserModel
from app.services import email_service
from app.services.activity_service import log_activity, notifications_updated_this_request
from app.services.agreement_template import label_for

logger = logging.getLogger(__name__)

LINK_DEFAULT_DAYS = 30


def ensure_sign_token(a: AgreementModel) -> str:
    """Create (or extend) the signing link for a sent agreement."""
    if not a.sign_token:
        a.sign_token = secrets.token_urlsafe(32)
    if a.valid_until:
        a.sign_token_expires_at = datetime.combine(a.valid_until, time(23, 59, 59), tzinfo=timezone.utc)
    else:
        a.sign_token_expires_at = datetime.now(timezone.utc) + timedelta(days=LINK_DEFAULT_DAYS)
    return a.sign_token


def link_expired(a: AgreementModel) -> bool:
    if not a.sign_token_expires_at:
        return False
    exp = a.sign_token_expires_at if a.sign_token_expires_at.tzinfo else a.sign_token_expires_at.replace(tzinfo=timezone.utc)
    return exp < datetime.now(timezone.utc)


def sign_url(a: AgreementModel) -> str | None:
    if not a.sign_token:
        return None
    return f"{get_settings().frontend_url.rstrip('/')}/sign/{a.sign_token}"


def acceptance_hash(a: AgreementModel, signer_name: str, accepted_at: datetime) -> str:
    payload = json.dumps(
        {"number": a.number, "title": a.title, "clauses": a.clauses or [], "signer": signer_name, "at": accepted_at.isoformat()},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_acceptance(
    db: Session, a: AgreementModel, *, signer_name: str, signer_email: str | None, signer_title: str | None,
    ip: str | None, user_agent: str | None, method: str, actor_user_id=None,
) -> None:
    now = datetime.now(timezone.utc)
    a.status = "signed"
    a.accepted_at = now
    a.accepted_by_name = signer_name
    a.signer_email = signer_email or a.signer_email or (a.client.contact_email if a.client else None)
    a.signer_title = signer_title
    a.accepted_ip = (ip or "")[:64] or None
    a.accepted_user_agent = (user_agent or "")[:255] or None
    a.acceptance_method = method
    a.acceptance_hash = acceptance_hash(a, signer_name, now)
    via = {"link": "via the signing link", "portal": "via the client portal"}.get(method, "by signature")
    _notify_creator(db, a, f"signed by {signer_name} {via}")
    log_activity(db, actor_user_id or a.created_by, "agreement_signed", "agreement", a.id, details=f"{a.number} signed by {signer_name} {via}")


def record_decline(db: Session, a: AgreementModel, reason: str | None, actor_label: str, actor_user_id=None) -> None:
    a.status = "declined"
    a.decline_reason = reason
    _notify_creator(db, a, f"declined {actor_label}" + (f": {reason}" if reason else ""))
    log_activity(db, actor_user_id or a.created_by, "agreement_declined", "agreement", a.id, details=f"{a.number} declined {actor_label}")


def _notify_creator(db: Session, a: AgreementModel, outcome: str) -> None:
    if not a.created_by:
        return
    msg = f'{label_for(a.agreement_type)} {a.number} "{a.title}" was {outcome}'
    if a.agreement_type == "nda" and a.client is not None and getattr(a.client, "status", "active") == "prospect" and a.status == "signed":
        msg += ". You can now accept the client."
    db.add(NotificationModel(user_id=a.created_by, title="Agreement update", message=msg, link="/agreements", type="agreement", reference_id=None))
    notifications_updated_this_request.set(True)
    creator = db.query(UserModel).filter(UserModel.id == a.created_by).first()
    if creator:
        email_service.send_notification(creator.email, "Agreement update", msg, "/agreements")


def send_executed_copy(a: AgreementModel) -> None:
    """Email the signer their signed copy. Never raises: the signature is already recorded."""
    to = a.signer_email or (a.client.contact_email if a.client else None)
    if not to:
        return
    try:
        from app.services.pdf_service import build_agreement_pdf
        label = label_for(a.agreement_type)
        body = (
            f"<p>Thank you. <b>{a.title}</b> ({a.number}) was signed by {a.accepted_by_name} on "
            f"{a.accepted_at:%d %B %Y at %H:%M} UTC.</p>"
            "<p>Your signed copy is attached. Keep it with your records.</p>"
        )
        url = sign_url(a)
        email_service.send_email(
            to, f"Signed copy: {label} {a.number}",
            email_service._build_html(f"Signed: {a.title}", body, "View the agreement" if url else None, url),
            f"{a.title} ({a.number}) was signed by {a.accepted_by_name}. Your signed copy is attached.",
            attachments=[(f"{a.number}.pdf", build_agreement_pdf(a))],
        )
    except Exception:
        logger.exception("could not email the executed copy for %s", a.number)


def send_for_signature(a: AgreementModel, to: str) -> None:
    """The email a prospect or client gets when an agreement is sent."""
    from app.services.pdf_service import build_agreement_pdf
    label = label_for(a.agreement_type)
    url = sign_url(a)
    body = (
        f"<p>Please review and sign the <b>{label}</b> <b>{a.title}</b> ({a.number}).</p>"
        "<p>Open the link below, read the terms, type your name and confirm. You will receive a signed copy by email "
        "straight away. A PDF of the unsigned document is attached for reference.</p>"
        + (f"<p>Please sign by <b>{a.valid_until:%d %B %Y}</b>.</p>" if a.valid_until else "")
    )
    email_service.send_email(
        to, f"Please sign: {label} {a.number}",
        email_service._build_html(f"{label}: {a.title}", body, "Review and sign", url),
        f"Please review and sign {label} {a.number}: {a.title}\n{url or ''}",
        attachments=[(f"{a.number}.pdf", build_agreement_pdf(a))],
    )
