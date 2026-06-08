from sqlalchemy import inspect, text

from app.database import engine


SPORT_TABLES = ("competitions", "monitored_competitions")


def ensure_sport_columns():
    """
    Migrazione runtime idempotente per supporto multi-sport.

    Serve per database già esistenti in produzione, soprattutto Render/PostgreSQL,
    dove il codice nuovo usa competitions.sport e monitored_competitions.sport
    ma le colonne potrebbero non essere ancora presenti.
    """
    with engine.begin() as conn:
        inspector = inspect(conn)

        for table_name in SPORT_TABLES:
            existing_tables = inspector.get_table_names()
            if table_name not in existing_tables:
                print(f"[runtime] skipped sport column migration: table {table_name} not found")
                continue

            columns = {column["name"] for column in inspector.get_columns(table_name)}

            if "sport" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        "ADD COLUMN sport VARCHAR NOT NULL DEFAULT 'football'"
                    )
                )
                print(f"[runtime] added {table_name}.sport")

            conn.execute(
                text(
                    f"UPDATE {table_name} "
                    "SET sport = 'football' "
                    "WHERE sport IS NULL OR sport = ''"
                )
            )

    print("[runtime] ensured sport columns")
