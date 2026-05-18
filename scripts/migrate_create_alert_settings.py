import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine


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


def run():
    with engine.connect() as conn:
        conn.exec_driver_sql(CREATE_ALERT_SETTINGS_SQL)

        existing = conn.exec_driver_sql("SELECT COUNT(*) FROM alert_settings").scalar()
        if existing == 0:
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

    print("alert_settings table ready")


if __name__ == "__main__":
    run()
