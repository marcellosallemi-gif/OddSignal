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

CREATE_NOTIFICATION_RECIPIENTS_SQL = """
CREATE TABLE IF NOT EXISTS notification_recipients (
    id INTEGER PRIMARY KEY,
    channel VARCHAR NOT NULL,
    recipient_value VARCHAR NOT NULL,
    label VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT 1,
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
        monitored_competition_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(monitored_competitions)").fetchall()
        }
        if "provider_league_slug" not in monitored_competition_columns:
            conn.exec_driver_sql(
                "ALTER TABLE monitored_competitions ADD COLUMN provider_league_slug VARCHAR"
            )

        conn.exec_driver_sql(CREATE_NOTIFICATION_RECIPIENTS_SQL)
        conn.exec_driver_sql(CREATE_ALERT_SETTINGS_SQL)

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
        "notification_recipients": "ready",
        "alert_settings": "ready",
    }


def should_seed_demo_data() -> bool:
    return os.getenv("SEED_DEMO_DATA", "0") == "1"
