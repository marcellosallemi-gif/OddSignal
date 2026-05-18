import os

from dotenv import load_dotenv

from app.database import engine


ODDS_SNAPSHOT_METADATA_COLUMNS = {
    "provider_event_id": "TEXT",
    "line": "FLOAT",
    "provider_updated_at": "DATETIME",
    "raw_payload": "TEXT",
}


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

        conn.exec_driver_sql(CREATE_NOTIFICATION_LOGS_SQL)
        conn.commit()

    return {
        "status": "ok",
        "added_odds_snapshot_columns": added_columns,
        "notification_logs": "ready",
    }


def should_seed_demo_data() -> bool:
    return os.getenv("SEED_DEMO_DATA", "0") == "1"
