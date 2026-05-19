import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine
from app.runtime import CREATE_MONITORED_MARKETS_SQL, DEFAULT_MONITORED_MARKETS


def migrate():
    with engine.connect() as conn:
        conn.exec_driver_sql(CREATE_MONITORED_MARKETS_SQL)
        existing_markets = conn.exec_driver_sql(
            "SELECT COUNT(*) FROM monitored_markets"
        ).scalar()

        if existing_markets == 0:
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

        conn.commit()

    print("monitored_markets table ready")


if __name__ == "__main__":
    migrate()
