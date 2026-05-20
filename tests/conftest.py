import os
import tempfile
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from httpx._client import USE_CLIENT_DEFAULT


TEST_DB_DIR = tempfile.mkdtemp(prefix="calcoloquote-tests-")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.sqlite")
TEST_APP_USERNAME = "admin"
TEST_APP_PASSWORD = "change-me"

os.environ["DATABASE_URL"] = "sqlite:///{}".format(TEST_DB_PATH)
os.environ.setdefault("SEED_DEMO_DATA", "1")
os.environ.setdefault("ODDS_SCHEDULER_ENABLED", "0")
os.environ.setdefault("APP_USERNAME", TEST_APP_USERNAME)
os.environ.setdefault("APP_PASSWORD", TEST_APP_PASSWORD)


_original_request = TestClient.request


def _is_public_test_path(url):
    path = urlsplit(str(url)).path
    return path == "/health" or path == "/static" or path.startswith("/static/")


def _request_with_default_auth(self, method, url, **kwargs):
    headers = kwargs.get("headers") or {}
    has_authorization = any(
        header_name.lower() == "authorization"
        for header_name in headers
    )

    auth = kwargs.get("auth", USE_CLIENT_DEFAULT)

    if (
        auth is USE_CLIENT_DEFAULT
        and not has_authorization
        and not _is_public_test_path(url)
    ):
        kwargs["auth"] = (TEST_APP_USERNAME, TEST_APP_PASSWORD)

    return _original_request(self, method, url, **kwargs)


TestClient.request = _request_with_default_auth
