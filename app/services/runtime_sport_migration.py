from sqlalchemy import inspect, text

from app.database import engine


SPORT_COLUMN_TABLES = ("competitions", "monitored_competitions", "monitored_markets")

FOOTBALL_MARKETS = {
    "1X2",
    "Doppia chance",
    "Double Chance",
    "Pareggio escluso",
    "Draw No Bet",
    "Goal/No Goal",
    "Handicap asiatico",
    "Handicap europeo",
    "European Handicap",
    "Over/Under 0.5",
    "Over/Under 1.5",
    "Over/Under 2.5",
    "Over/Under 3.5",
    "Risultato esatto",
    "Risultato primo tempo",
    "Primo tempo/finale",
    "Totale corner",
    "Handicap corner",
    "Totale cartellini",
    "Marcatori",
    "Primo marcatore",
    "Entrambe segnano nel primo tempo",
}

TENNIS_MARKETS = [
    "Vincitore match",
    "Handicap giochi",
    "Totale giochi",
    "Vincitore primo set",
    "Totale giochi primo set",
    "Handicap set",
    "Risultato esatto set",
    "Tie-break nel match",
    "Numero set",
    "Vincitore secondo set",
    "Totale giochi secondo set",
    "Handicap giochi primo set",
    "Handicap giochi secondo set",
]


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _is_postgresql(conn) -> bool:
    return conn.dialect.name == "postgresql"


def _ensure_sport_column(conn, inspector, table_name: str):
    if not _table_exists(inspector, table_name):
        print(f"[runtime] skipped sport column migration: table {table_name} not found")
        return

    if not _column_exists(inspector, table_name, "sport"):
        conn.execute(
            text(
                f"ALTER TABLE {table_name} "
                "ADD COLUMN sport VARCHAR NOT NULL DEFAULT 'football'"
            )
        )
        print(f"[runtime] added {table_name}.sport")

    if _is_postgresql(conn):
        conn.execute(
            text(
                f"ALTER TABLE {table_name} "
                "ALTER COLUMN sport SET DEFAULT 'football'"
            )
        )

    conn.execute(
        text(
            f"UPDATE {table_name} "
            "SET sport = 'football' "
            "WHERE sport IS NULL OR sport = ''"
        )
    )


def _seed_tennis_markets(conn, inspector):
    if not _table_exists(inspector, "monitored_markets"):
        print("[runtime] skipped tennis market seed: monitored_markets not found")
        return

    conn.execute(
        text(
            "UPDATE monitored_markets "
            "SET sport = 'football' "
            "WHERE sport IS NULL OR sport = ''"
        )
    )

    for market_name in FOOTBALL_MARKETS:
        conn.execute(
            text(
                "UPDATE monitored_markets "
                "SET sport = 'football' "
                "WHERE market_name = :market_name"
            ),
            {"market_name": market_name},
        )

    for market_name in TENNIS_MARKETS:
        conn.execute(
            text(
                "INSERT INTO monitored_markets "
                "(sport, market_name, is_active, created_at) "
                "SELECT :sport, :market_name, :is_active, CURRENT_TIMESTAMP "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM monitored_markets WHERE market_name = :market_name"
                ")"
            ),
            {
                "sport": "tennis",
                "market_name": market_name,
                "is_active": False,
            },
        )


def ensure_sport_columns():
    """
    Migrazione runtime idempotente per supporto multi-sport.

    Garantisce sport su competizioni/campionati/mercati e crea i mercati tennis
    separati dai mercati calcio senza attivarli automaticamente.
    """
    with engine.begin() as conn:
        inspector = inspect(conn)

        for table_name in SPORT_COLUMN_TABLES:
            _ensure_sport_column(conn, inspector, table_name)

        inspector = inspect(conn)
        _seed_tennis_markets(conn, inspector)

    print("[runtime] ensured sport columns and sport-specific markets")
