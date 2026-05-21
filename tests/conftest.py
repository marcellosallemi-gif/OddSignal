import os
os.environ["ODDS_SCHEDULER_ENABLED"] = "0"
os.environ["TELEGRAM_AUTO_SYNC_ENABLED"] = "0"
os.environ["PROVIDER_COMPETITIONS_AUTO_REFRESH_ENABLED"] = "0"
import tempfile

os.environ["APP_AUTH_ENABLED"] = "0"


TEST_DB_DIR = tempfile.mkdtemp(prefix="calcoloquote-tests-")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.sqlite")
TEST_APP_USERNAME = "admin"
TEST_APP_PASSWORD = "change-me"

os.environ["DATABASE_URL"] = "sqlite:///{}".format(TEST_DB_PATH)
os.environ.setdefault("SEED_DEMO_DATA", "1")
os.environ.setdefault("ODDS_SCHEDULER_ENABLED", "0")
os.environ.setdefault("APP_USERNAME", TEST_APP_USERNAME)
os.environ.setdefault("APP_PASSWORD", TEST_APP_PASSWORD)
os.environ.setdefault("APP_SESSION_SECRET", "test-session-secret")
