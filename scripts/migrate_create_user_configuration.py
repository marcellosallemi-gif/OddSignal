import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine


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


def run():
    with engine.connect() as conn:
        conn.exec_driver_sql(CREATE_MONITORED_COMPETITIONS_SQL)
        existing_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(monitored_competitions)").fetchall()
        }
        if "provider_league_slug" not in existing_columns:
            conn.exec_driver_sql(
                "ALTER TABLE monitored_competitions ADD COLUMN provider_league_slug VARCHAR"
            )

        conn.exec_driver_sql(CREATE_NOTIFICATION_RECIPIENTS_SQL)
        conn.commit()

    print("user configuration tables ready")


if __name__ == "__main__":
    run()
