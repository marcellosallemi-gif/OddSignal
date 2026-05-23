import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.models import Alert, NotificationLog, NotificationRecipient


TELEGRAM_SAFE_MESSAGE_LIMIT = 3500
TELEGRAM_TRUNCATION_SUFFIX = "\n…contenuto abbreviato"


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


def telegram_label_from_chat(chat):
    first_name = chat.get("first_name") or ""
    last_name = chat.get("last_name") or ""
    username = chat.get("username")

    full_name = " ".join([part for part in [first_name, last_name] if part]).strip()

    if full_name and username:
        return f"{full_name} (@{username})"

    if username:
        return f"@{username}"

    if full_name:
        return full_name

    return "Account Telegram"


def sync_telegram_recipients_from_payload(db, payload):
    chats_by_id = {}

    for update in payload.get("result", []):
        message = update.get("message") or {}
        chat = message.get("chat") or {}

        if chat.get("type") != "private":
            continue

        chat_id = chat.get("id")
        if chat_id is None:
            continue

        chats_by_id[str(chat_id)] = chat

    synced = []

    for recipient_value, chat in chats_by_id.items():
        label = telegram_label_from_chat(chat)

        existing = (
            db.query(NotificationRecipient)
            .filter(
                NotificationRecipient.channel == "telegram",
                NotificationRecipient.recipient_value == recipient_value,
            )
            .first()
        )

        updated_profile = False

        if existing:
            updated_profile = existing.label != label
            existing.label = label
            recipient = existing
        else:
            recipient = NotificationRecipient(
                channel="telegram",
                recipient_value=recipient_value,
                label=label,
                is_active=False,
                status="pending",
                created_at=_utc_now_naive(),
            )
            db.add(recipient)

        db.flush()
        synced.append(
            {
                "id": recipient.id,
                "label": label,
                "is_active": recipient.is_active,
                "status": recipient.status,
                "recipient_value": recipient.recipient_value,
                "updated_profile": updated_profile,
            }
        )

    db.commit()

    updated_recipients_count = len(
        [item for item in synced if item.get("updated_profile")]
    )

    return {
        "status": "completed",
        "synced_count": len(synced),
        "updated_recipients_count": updated_recipients_count,
        "recipients": synced,
    }


def sync_telegram_recipients_from_telegram(db):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return {
            "status": "skipped",
            "error": "telegram_not_configured",
            "message": "TELEGRAM_BOT_TOKEN non configurato: sync Telegram saltato.",
            "synced_count": 0,
            "recipients": [],
        }

    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            timeout=15,
        )
    except httpx.RequestError as exc:
        return {
            "status": "failed",
            "error": "telegram_request_failed",
            "message": "Impossibile contattare Telegram. Riprova tra poco.",
            "detail": str(exc),
            "synced_count": 0,
            "recipients": [],
        }

    if response.status_code >= 400:
        return {
            "status": "failed",
            "error": "telegram_api_error",
            "message": "Telegram ha rifiutato la richiesta. Verifica il token del bot.",
            "http_status": response.status_code,
            "synced_count": 0,
            "recipients": [],
        }

    return sync_telegram_recipients_from_payload(db, response.json())


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

    if market_name.startswith("European Handicap"):
        suffix = market_name.replace("European Handicap", "", 1).strip()
        return "Handicap europeo" + (f" {suffix}" if suffix else "")

    return market_name


def readable_line_label(market_name: str) -> Optional[str]:
    if not market_name:
        return None

    market_name = str(market_name)
    for prefix in ["European Handicap", "Totals", "Spread"]:
        if market_name.startswith(prefix + " "):
            return market_name.replace(prefix, "", 1).strip()

    return None


def readable_selection_label(
    market_name: str,
    selection: str,
    home_team: Optional[str] = None,
    away_team: Optional[str] = None,
) -> str:
    selection_value = str(selection or "").strip()
    selection_key = selection_value.lower().replace("_", " ").replace("-", " ")
    line = readable_line_label(market_name)
    home_label = home_team or "Casa"
    away_label = away_team or "Trasferta"

    if not selection_value:
        return "Selezione non specificata"

    if market_name == "ML":
        return {
            "home": f"1 - {home_label}",
            "draw": "X - Pareggio",
            "away": f"2 - {away_label}",
            "1": f"1 - {home_label}",
            "x": "X - Pareggio",
            "2": f"2 - {away_label}",
        }.get(selection_key, selection_value)

    if market_name.startswith("Totals"):
        label = {
            "over": "Over",
            "under": "Under",
        }.get(selection_key, selection_value)
        return f"{label} {line}" if line else label

    if market_name.startswith("Both Teams To Score"):
        return {
            "goal": "Goal",
            "yes": "Goal",
            "no goal": "No Goal",
            "no": "No Goal",
        }.get(selection_key, selection_value)

    if market_name.startswith("Double Chance"):
        return {
            "1x": f"1X - {home_label} o Pareggio",
            "x2": f"X2 - Pareggio o {away_label}",
            "12": f"12 - {home_label} o {away_label}",
        }.get(selection_key, selection_value)

    if market_name.startswith("Spread") or market_name.startswith("European Handicap"):
        label = {
            "home": home_label,
            "draw": "Pareggio",
            "away": away_label,
            "1": home_label,
            "x": "Pareggio",
            "2": away_label,
        }.get(selection_key, selection_value)
        return f"{label} handicap {line}" if line else label

    return selection_value


def build_alert_message(alert: Alert) -> str:
    event = alert.event
    competition = event.competition.name if event and event.competition else "Unknown competition"

    home_team = event.home_team.name if event and event.home_team else "Unknown home"
    away_team = event.away_team.name if event and event.away_team else "Unknown away"

    direction_label = "aumento" if alert.direction == "increase" else "diminuzione"
    line_label = readable_line_label(alert.market)
    line_text = f"Linea: {line_label}\n" if line_label else ""

    return (
        "Alert quote calcio\n"
        "\n"
        f"Tipo: {alert.alert_type}\n"
        f"Evento: {home_team} vs {away_team}\n"
        f"Competizione: {competition}\n"
        f"Bookmaker: {alert.bookmaker}\n"
        f"Mercato: {readable_market_label(alert.market)}\n"
        f"Selezione: {readable_selection_label(alert.market, alert.selection, home_team, away_team)}\n"
        f"{line_text}"
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


def build_alerts_summary_message(alerts: List[Alert], max_items: int = 500) -> str:
    return "\n\n".join(build_alerts_summary_messages(alerts, max_items=max_items))


def _truncate_text(value: str, limit: int = TELEGRAM_SAFE_MESSAGE_LIMIT) -> str:
    if len(value) <= limit:
        return value

    available_length = max(0, limit - len(TELEGRAM_TRUNCATION_SUFFIX))
    return value[:available_length].rstrip() + TELEGRAM_TRUNCATION_SUFFIX


def _compact_alert_summary_block(alert: Alert, index: int) -> str:
    direction_label = "aumento" if alert.direction == "increase" else "diminuzione"
    line_label = readable_line_label(alert.market)
    line_items = [f"Linea: {line_label}"] if line_label else []
    event = alert.event
    home_team = event.home_team.name if event and event.home_team else None
    away_team = event.away_team.name if event and event.away_team else None

    block = "\n".join(
        [
            f"{index}. Evento: {_alert_event_label(alert)}",
            f"Mercato: {readable_market_label(alert.market)}",
            f"Selezione: {readable_selection_label(alert.market, alert.selection, home_team, away_team)}",
            *line_items,
            f"Bookmaker: {alert.bookmaker}",
            f"Quota precedente: {alert.previous_odds}",
            f"Quota attuale: {alert.current_odds}",
            f"Variazione: {alert.variation_percent}% ({direction_label})",
            f"Tipo alert: {alert.alert_type}",
            f"Provider: {alert.provider}",
        ]
    )

    return _truncate_text(block, TELEGRAM_SAFE_MESSAGE_LIMIT - 500)


def _build_alerts_summary_part(
    part_number: int,
    parts_count: int,
    total_alerts: int,
    alert_blocks: List[str],
    truncate: bool = True,
) -> str:
    lines = [
        f"OddSignal - Alert quote (parte {part_number}/{parts_count})",
        f"Alert totali generati: {total_alerts}",
        f"Alert in questa parte: {len(alert_blocks)}",
        "",
    ]
    lines.extend(alert_blocks)

    message = "\n\n".join(lines)
    if not truncate:
        return message

    return _truncate_text(message)


def build_alerts_summary_messages(alerts: List[Alert], max_items: int = 500) -> List[str]:
    if not alerts:
        return ["Nessun alert quote calcio rilevato."]

    sorted_alerts = sorted(
        alerts,
        key=lambda alert: abs(alert.variation_percent or 0),
        reverse=True,
    )
    alert_blocks = [
        _compact_alert_summary_block(alert, index)
        for index, alert in enumerate(sorted_alerts[:max_items], start=1)
    ]

    remaining = len(alerts) - max_items
    if remaining > 0:
        alert_blocks.append(f"Altri {remaining} alert non inclusi per limite riepilogo.")

    parts = []
    current_blocks = []

    for alert_block in alert_blocks:
        candidate_blocks = current_blocks + [alert_block]
        candidate_message = _build_alerts_summary_part(
            part_number=999,
            parts_count=999,
            total_alerts=len(alerts),
            alert_blocks=candidate_blocks,
            truncate=False,
        )

        if current_blocks and len(candidate_message) > TELEGRAM_SAFE_MESSAGE_LIMIT:
            parts.append(current_blocks)
            current_blocks = [alert_block]
        else:
            current_blocks = candidate_blocks

    if current_blocks:
        parts.append(current_blocks)

    parts_count = len(parts)
    return [
        _build_alerts_summary_part(
            part_number=index,
            parts_count=parts_count,
            total_alerts=len(alerts),
            alert_blocks=part_blocks,
        )
        for index, part_blocks in enumerate(parts, start=1)
    ]


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
    message = _truncate_text(message)
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
    message = _truncate_text(message)
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

    messages = build_alerts_summary_messages(alerts)
    message = messages[0]
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

    results = []
    for recipient in recipients:
        for part_index, part_message in enumerate(messages, start=1):
            result = _send_single_telegram_message(
                db=db,
                alert=log_alert,
                bot_token=bot_token,
                recipient=recipient,
                message=part_message,
            )
            result["part"] = part_index
            result["parts_count"] = len(messages)
            results.append(result)

    messages_sent = len([item for item in results if item["status"] == "sent"])
    messages_failed = len([item for item in results if item["status"] == "failed"])

    return {
        "status": "completed",
        "channel": "telegram",
        "logs_created": len(results),
        "recipients_count": len(recipients),
        "messages_attempted": len(results),
        "messages_sent": messages_sent,
        "messages_failed": messages_failed,
        "parts_count": len(messages),
        "sent": messages_sent,
        "failed": messages_failed,
        "alerts_included": len(alerts),
        "results": results,
    }
