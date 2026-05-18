import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine


def run():
    with engine.connect() as conn:
        existing_columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(competitions)").fetchall()
        }

        added = []

        if "provider_league_slug" not in existing_columns:
            conn.exec_driver_sql(
                "ALTER TABLE competitions ADD COLUMN provider_league_slug VARCHAR"
            )
            added.append("provider_league_slug")

        conn.commit()

    print("added_columns:", ", ".join(added) if added else "none")


if __name__ == "__main__":
    run()
