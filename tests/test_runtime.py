from app import runtime


def test_should_seed_demo_data_defaults_to_false(monkeypatch):
    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)

    assert runtime.should_seed_demo_data() is False


def test_should_seed_demo_data_enabled(monkeypatch):
    monkeypatch.setenv("SEED_DEMO_DATA", "1")

    assert runtime.should_seed_demo_data() is True


def test_runtime_migrations_returns_status():
    result = runtime.run_runtime_migrations()

    assert result["status"] in {"ok", "skipped"}
