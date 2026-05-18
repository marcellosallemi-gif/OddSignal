import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.models import Alert, NotificationLog, NotificationRecipient


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN"))


def get_active_telegram_recipients(db) -> List[str]:
    recipients = [
        item.recipient_value
        for item in db.query(NotificationRecipient)
        .filter(
            NotificationRecipient.channel == "telegram",
            NotificationRecipient.is_active.is_(True),
        )
        .all()
        if item.recipient_value
    ]

    fallback_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if fallback_chat_id and fallback_chat_id not in recipients:
        recipients.append(fallback_chat_id)

    return recipients


def build_alert_message(alert: Alert) -> str:
    event = alert.event
    competition = event.competition.name if event and event.competition else "Unknown competition"

    home_team = event.home_team.name if event and event.home_team else "Unknown home"
    away_team = event.away_team.name if event and event.away_team else "Unknown away"

    direction_label = "aumento" if alert.direction == "increase" else "diminuzione"

    return (
        "Alert quote calcio\n"
        "\n"
        f"Tipo: {alert.alert_type}\n"
        f"Evento: {home_team} vs {away_team}\n"
        f"Competizione: {competition}\n"
        f"Bookmaker: {alert.bookmaker}\n"
        f"Mercato: {alert.market}\n"
        f"Selezione: {alert.selection}\n"
        f"Variazione: {alert.variation_percent}% ({direction_label})\n"
        f"Quota precedente: {alert.previous_odds}\n"
        f"Quota attuale: {alert.current_odds}\n"
        f"Provider: {alert.provider}"
    )


def save_notification_log(
    db,
    alert: Alert,
    status: str,
    message: str,
    recipient: Optional[str] = None,
    error_message: Optional[str] = None,
):
    log = NotificationLog(
        alert_id=alert.id,
        event_id=alert.event_id,
        channel="telegram",
        status=status,
        recipient=recipient,
        message=message,
        error_message=error_message,
        sent_at=_utc_now_naive(),
    )
    db.add(log)
    db.flush()
    return log


def _send_single_telegram_message(
    db,
    alert: Alert,
    bot_token: str,
    recipient: str,
    message: str,
):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": recipient,
        "text": message,
        "disable_web_page_preview": True,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, json=payload)
    except httpx.RequestError as exc:
        save_notification_log(
            db=db,
            alert=alert,
            status="failed",
            recipient=recipient,
            message=message,
            error_message=str(exc),
        )
        return {
            "status": "failed",
            "recipient": recipient,
            "error": str(exc),
        }

    if response.status_code >= 400:
        save_notification_log(
            db=db,
            alert=alert,
            status="failed",
            recipient=recipient,
            message=message,
            error_message=response.text[:500],
        )
        return {
            "status": "failed",
            "recipient": recipient,
            "http_status": response.status_code,
            "error": response.text[:500],
        }

    save_notification_log(
        db=db,
        alert=alert,
        status="sent",
        recipient=recipient,
        message=message,
        error_message=None,
    )

    return {
        "status": "sent",
        "recipient": recipient,
    }


def send_telegram_alert(db, alert: Alert):
    message = build_alert_message(alert)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        save_notification_log(
            db=db,
            alert=alert,
            status="skipped",
            recipient=None,
            message=message,
            error_message="Telegram bot token is not configured.",
        )
        return {
            "status": "skipped",
            "channel": "telegram",
            "logs_created": 1,
            "reason": "Telegram bot token is not configured.",
        }

    recipients = get_active_telegram_recipients(db)
    if not recipients:
        save_notification_log(
            db=db,
            alert=alert,
            status="skipped",
            recipient=None,
            message=message,
            error_message="No active Telegram recipients configured.",
        )
        return {
            "status": "skipped",
            "channel": "telegram",
            "logs_created": 1,
            "reason": "No active Telegram recipients configured.",
        }

    results = [
        _send_single_telegram_message(
            db=db,
            alert=alert,
            bot_token=bot_token,
            recipient=recipient,
            message=message,
        )
        for recipient in recipients
    ]

    return {
        "status": "completed",
        "channel": "telegram",
        "logs_created": len(results),
        "sent": len([item for item in results if item["status"] == "sent"]),
        "failed": len([item for item in results if item["status"] == "failed"]),
        "results": results,
    }
