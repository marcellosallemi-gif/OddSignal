import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine


CREATE_TABLE_SQL = """
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


def run():
    with engine.connect() as conn:
        conn.exec_driver_sql(CREATE_TABLE_SQL)
        conn.commit()

    print("notification_logs table ready")


if __name__ == "__main__":
    run()
