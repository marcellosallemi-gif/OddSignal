import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.models import Alert, NotificationLog, NotificationRecipient


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def is_telegram_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN"))


def get_active_telegram_recipients(db, include_fallback: bool = True) -> List[str]:
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
    if include_fallback and fallback_chat_id and fallback_chat_id not in recipients:
        recipients.append(fallback_chat_id)

    return recipients


def readable_market_label(market_name: str) -> str:
    if not market_name:
        return "Mercato non specificato"

    market_name = str(market_name)

    if market_name == "ML":
        return "1X2"

    if market_name.startswith("Totals"):
        suffix = market_name.replace("Totals", "", 1).strip()
        return "Over/Under" + (f" {suffix}" if suffix else "")

    if market_name.startswith("Both Teams To Score"):
        return "Goal/No Goal"

    if market_name.startswith("Spread"):
        suffix = market_name.replace("Spread", "", 1).strip()
        return "Handicap" + (f" {suffix}" if suffix else "")

    return market_name


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
        f"Mercato: {readable_market_label(alert.market)}\n"
        f"Selezione: {alert.selection}\n"
        f"Variazione: {alert.variation_percent}% ({direction_label})\n"
        f"Quota precedente: {alert.previous_odds}\n"
        f"Quota attuale: {alert.current_odds}\n"
        f"Provider: {alert.provider}"
    )


def _alert_event_label(alert: Alert) -> str:
    event = alert.event
    home_team = event.home_team.name if event and event.home_team else "Unknown home"
    away_team = event.away_team.name if event and event.away_team else "Unknown away"
    return f"{home_team} vs {away_team}"


def _alert_competition_label(alert: Alert) -> str:
    event = alert.event
    return event.competition.name if event and event.competition else "Unknown competition"


def build_alerts_summary_message(alerts: List[Alert], max_items: int = 50) -> str:
    if not alerts:
        return "Nessun alert quote calcio rilevato."

    critical_count = len([alert for alert in alerts if alert.alert_type == "critical_alert"])
    standard_count = len([alert for alert in alerts if alert.alert_type == "standard_alert"])

    lines = [
        f"Alert quote calcio: {len(alerts)} movimenti validi rilevati",
        "",
        f"Critici: {critical_count}",
        f"Standard: {standard_count}",
        "",
        "Dettaglio alert:",
    ]

    sorted_alerts = sorted(
        alerts,
        key=lambda alert: abs(alert.variation_percent or 0),
        reverse=True,
    )

    for index, alert in enumerate(sorted_alerts[:max_items], start=1):
        severity_label = " CRITICO" if alert.alert_type == "critical_alert" else ""
        direction_label = "aumento" if alert.direction == "increase" else "diminuzione"
        competition = _alert_competition_label(alert)
        event_label = _alert_event_label(alert)

        lines.extend(
            [
                "",
                f"{index}. {competition}",
                f"Evento: {event_label}",
                f"Tipo: {alert.alert_type}{severity_label}",
                f"Bookmaker: {alert.bookmaker}",
                f"Mercato: {readable_market_label(alert.market)}",
                f"Selezione: {alert.selection}",
                f"Variazione: {alert.variation_percent}% ({direction_label})",
                f"Quota precedente: {alert.previous_odds}",
                f"Quota attuale: {alert.current_odds}",
            ]
        )

    remaining = len(alerts) - max_items
    if remaining > 0:
        lines.extend(
            [
                "",
                f"Altri {remaining} alert non inclusi per limite messaggio.",
            ]
        )

    return "\n".join(lines)


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


def send_telegram_message(bot_token: str, recipient: str, message: str):
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
        return {
            "status": "failed",
            "recipient": recipient,
            "error": str(exc),
        }

    if response.status_code >= 400:
        return {
            "status": "failed",
            "recipient": recipient,
            "http_status": response.status_code,
            "error": response.text[:500],
        }

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


def send_telegram_alert_summary(db, alerts: List[Alert]):
    if not alerts:
        return {
            "status": "skipped",
            "channel": "telegram",
            "logs_created": 0,
            "reason": "No alerts to notify.",
        }

    message = build_alerts_summary_message(alerts)
    log_alert = alerts[0]

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        save_notification_log(
            db=db,
            alert=log_alert,
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
            alert=log_alert,
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
            alert=log_alert,
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
        "alerts_included": len(alerts),
        "results": results,
    }
