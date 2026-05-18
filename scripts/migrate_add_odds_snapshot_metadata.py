import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine


COLUMNS = {
    "provider_event_id": "TEXT",
    "line": "FLOAT",
    "provider_updated_at": "DATETIME",
    "raw_payload": "TEXT",
}


def run():
    with engine.connect() as conn:
        existing_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(odds_snapshots)").fetchall()
        }

        added = []

        for column_name, column_type in COLUMNS.items():
            if column_name not in existing_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE odds_snapshots ADD COLUMN {column_name} {column_type}"
                )
                added.append(column_name)

        conn.commit()

    print("added_columns:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    run()
