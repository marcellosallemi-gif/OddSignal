import os

from dotenv import load_dotenv

from app.database import engine


ODDS_SNAPSHOT_METADATA_COLUMNS = {
    "provider_event_id": "TEXT",
    "line": "FLOAT",
    "provider_updated_at": "DATETIME",
    "raw_payload": "TEXT",
}


COMPETITION_METADATA_COLUMNS = {
    "provider_league_slug": "VARCHAR",
}




CREATE_MONITORED_COMPETITIONS_SQL = """
CREATE TABLE IF NOT EXISTS monitored_competitions (
    id INTEGER PRIMARY KEY,
    competition_name VARCHAR NOT NULL UNIQUE,
    country VARCHAR,
    provider VARCHAR NOT NULL DEFAULT 'odds_api_io',
    provider_league_slug VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
)
"""


DEFAULT_MONITORED_MARKETS = (
    "ML",
    "Totals",
    "Both Teams To Score",
    "Spread",
)


CREATE_MONITORED_MARKETS_SQL = """
CREATE TABLE IF NOT EXISTS monitored_markets (
    id INTEGER PRIMARY KEY,
    market_name VARCHAR NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
)
"""




CREATE_ALERT_SETTINGS_SQL = """
CREATE TABLE IF NOT EXISTS alert_settings (
    id INTEGER PRIMARY KEY,
    min_percent FLOAT NOT NULL DEFAULT 8.0,
    max_percent FLOAT NOT NULL DEFAULT 15.0,
    critical_percent FLOAT NOT NULL DEFAULT 15.0,
    deduplication_minutes INTEGER NOT NULL DEFAULT 30,
    created_at DATETIME NOT NULL
)
"""

CREATE_SCHEDULER_SETTINGS_SQL = """
CREATE TABLE IF NOT EXISTS scheduler_settings (
    id INTEGER PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT 0,
    poll_interval_seconds INTEGER NOT NULL DEFAULT 300,
    event_limit INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
)
"""

CREATE_PROVIDER_PLAN_SETTINGS_SQL = """
CREATE TABLE IF NOT EXISTS provider_plan_settings (
    id INTEGER PRIMARY KEY,
    plan_name VARCHAR NOT NULL DEFAULT 'Free',
    hourly_request_limit INTEGER,
    max_bookmakers INTEGER NOT NULL DEFAULT 2,
    created_at DATETIME NOT NULL
)
"""

CREATE_NOTIFICATION_RECIPIENTS_SQL = """
CREATE TABLE IF NOT EXISTS notification_recipients (
    id INTEGER PRIMARY KEY,
    channel VARCHAR NOT NULL,
    recipient_value VARCHAR NOT NULL,
    label VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL
)
"""

CREATE_NOTIFICATION_LOGS_SQL = """
CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY,
    alert_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    channel VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    recipient VARCHAR,
    message TEXT NOT NULL,
    error_message TEXT,
    sent_at DATETIME NOT NULL,
    FOREIGN KEY(alert_id) REFERENCES alerts (id),
    FOREIGN KEY(event_id) REFERENCES events (id)
)
"""




def load_environment():
    load_dotenv()

def _is_sqlite() -> bool:
    return engine.url.drivername.startswith("sqlite")


def run_runtime_migrations() -> dict:
    if not _is_sqlite():
        return {
            "status": "skipped",
            "reason": "runtime migrations currently support sqlite only",
        }

    added_columns = []

    with engine.connect() as conn:
        odds_snapshots_exists = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='odds_snapshots'"
        ).fetchone()

        if odds_snapshots_exists:
            existing_columns = {
                row[1]
                for row in conn.exec_driver_sql("PRAGMA table_info(odds_snapshots)").fetchall()
            }

            for column_name, column_type in ODDS_SNAPSHOT_METADATA_COLUMNS.items():
                if column_name not in existing_columns:
                    conn.exec_driver_sql(
                        f"ALTER TABLE odds_snapshots ADD COLUMN {column_name} {column_type}"
                    )
                    added_columns.append(column_name)

        competitions_exists = conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='competitions'"
        ).fetchone()

        if competitions_exists:
            competition_columns = {
                row[1]
                for row in conn.exec_driver_sql("PRAGMA table_info(competitions)").fetchall()
            }

            for column_name, column_type in COMPETITION_METADATA_COLUMNS.items():
                if column_name not in competition_columns:
                    conn.exec_driver_sql(
                        f"ALTER TABLE competitions ADD COLUMN {column_name} {column_type}"
                    )

        conn.exec_driver_sql(CREATE_NOTIFICATION_LOGS_SQL)
        conn.exec_driver_sql(CREATE_MONITORED_COMPETITIONS_SQL)
        conn.exec_driver_sql(CREATE_MONITORED_MARKETS_SQL)
        existing_monitored_markets = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM monitored_markets"
        ).scalar()
        if existing_monitored_markets == 0:
            for market_name in DEFAULT_MONITORED_MARKETS:
                conn.exec_driver_sql(
                    """
                    INSERT INTO monitored_markets (
                        market_name,
                        is_active,
                        created_at
                    )
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    """,
                    (market_name,),
                )

        monitored_competition_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(monitored_competitions)").fetchall()
        }
        if "provider_league_slug" not in monitored_competition_columns:
            conn.exec_driver_sql(
                "ALTER TABLE monitored_competitions ADD COLUMN provider_league_slug VARCHAR"
            )

        conn.exec_driver_sql(CREATE_NOTIFICATION_RECIPIENTS_SQL)

        notification_recipient_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(notification_recipients)").fetchall()
        }
        if "status" not in notification_recipient_columns:
            conn.exec_driver_sql(
                "ALTER TABLE notification_recipients ADD COLUMN status VARCHAR NOT NULL DEFAULT 'active'"
            )
            conn.exec_driver_sql(
                "UPDATE notification_recipients SET status = 'disabled' WHERE is_active = 0"
            )

        conn.exec_driver_sql(CREATE_ALERT_SETTINGS_SQL)
        conn.exec_driver_sql(CREATE_SCHEDULER_SETTINGS_SQL)

        existing_scheduler_settings = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM scheduler_settings"
        ).scalar()
        if existing_scheduler_settings == 0:
            scheduler_enabled = 1 if os.getenv("ODDS_SCHEDULER_ENABLED", "0") == "1" else 0

            try:
                scheduler_interval = int(os.getenv("ODDS_POLL_INTERVAL_SECONDS", "300"))
            except ValueError:
                scheduler_interval = 300

            if scheduler_interval < 3:
                scheduler_interval = 3

            try:
                scheduler_event_limit = int(os.getenv("ODDS_SCHEDULER_EVENT_LIMIT", "1"))
            except ValueError:
                scheduler_event_limit = 1

            if scheduler_event_limit < 1:
                scheduler_event_limit = 1
            if scheduler_event_limit > 10:
                scheduler_event_limit = 10

            conn.exec_driver_sql(
                """
                INSERT INTO scheduler_settings (
                    enabled,
                    poll_interval_seconds,
                    event_limit,
                    created_at
                )
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (scheduler_enabled, scheduler_interval, scheduler_event_limit),
            )

        existing_alert_settings = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM alert_settings"
        ).scalar()
        if existing_alert_settings == 0:
            conn.exec_driver_sql(
                """
                INSERT INTO alert_settings (
                    min_percent,
                    max_percent,
                    critical_percent,
                    deduplication_minutes,
                    created_at
                )
                VALUES (8.0, 15.0, 15.0, 30, CURRENT_TIMESTAMP)
                """
            )

        conn.commit()

    return {
        "status": "ok",
        "added_odds_snapshot_columns": added_columns,
        "notification_logs": "ready",
        "monitored_competitions": "ready",
        "monitored_markets": "ready",
        "notification_recipients": "ready",
        "alert_settings": "ready",
        "scheduler_settings": "ready",
    }


def should_seed_demo_data() -> bool:
    return os.getenv("SEED_DEMO_DATA", "0") == "1"
