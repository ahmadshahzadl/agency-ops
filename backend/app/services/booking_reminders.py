"""Background reminder loop: once a minute, email invitees whose inbound booking is 24h / 1h away,
and once an hour notify finance users about recurring bills and salaries coming due.

Single-process by design (the app already runs one worker). Started from the FastAPI startup
hook when BOOKING_REMINDERS_ENABLED is true; safe to run alongside tests with it disabled.
"""
import logging
import threading
import time

from app.database import SessionLocal
from app.services import booking_service, recurring_expense_service

logger = logging.getLogger(__name__)

_INTERVAL = 60.0
_EXPENSE_INTERVAL = 3600.0
_thread: threading.Thread | None = None
_stop = threading.Event()
_last_expense_tick = 0.0


def run_once() -> int:
    db = SessionLocal()
    try:
        return booking_service.send_due_reminders(db)
    except Exception:
        logger.exception("booking reminder tick failed")
        db.rollback()
        return 0
    finally:
        db.close()


def run_expense_reminders_once() -> int:
    db = SessionLocal()
    try:
        return recurring_expense_service.send_due_reminders(db)
    except Exception:
        logger.exception("expense reminder tick failed")
        db.rollback()
        return 0
    finally:
        db.close()


def _loop() -> None:
    global _last_expense_tick
    # Small initial delay so the app finishes booting before the first DB hit.
    _stop.wait(10)
    while not _stop.is_set():
        n = run_once()
        if n:
            logger.info("sent %d booking reminder(s)", n)
        if time.monotonic() - _last_expense_tick >= _EXPENSE_INTERVAL:
            _last_expense_tick = time.monotonic()
            m = run_expense_reminders_once()
            if m:
                logger.info("sent %d expense reminder(s)", m)
        _stop.wait(_INTERVAL)


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="booking-reminders", daemon=True)
    _thread.start()
    logger.info("booking reminder scheduler started")


def stop() -> None:
    _stop.set()
