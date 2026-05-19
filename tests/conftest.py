import os
import tempfile


TEST_DB_DIR = tempfile.mkdtemp(prefix="calcoloquote-tests-")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.sqlite")

os.environ["DATABASE_URL"] = "sqlite:///{}".format(TEST_DB_PATH)
os.environ.setdefault("SEED_DEMO_DATA", "1")
os.environ.setdefault("ODDS_SCHEDULER_ENABLED", "0")
