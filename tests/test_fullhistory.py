import os

import pytest

os.environ.setdefault("DB_HOST", "test_host")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")
os.environ.setdefault("LASTFM_API_KEY", "test_api_key")
os.environ.setdefault("LASTFM_USERNAME", "test_user")

from src import fullhistory as fh


def make_track(n, artist="Radiohead"):
    return {
        "artist": {"#text": artist},
        "album": {"#text": "In Rainbows"},
        "name": f"Track{n}",
        "date": {"uts": str(1700000000 + n)},
    }


class FakeCopy:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def write_row(self, row):
        self.sink.append(row)


class FakeCursor:
    """Backs onto a shared dict standing in for durable Postgres state, so a
    fresh FakeConn (a "new runner") still sees checkpoint/scrobble data
    written by a previous one."""

    def __init__(self, db):
        self.db = db
        self.rowcount = 0
        self._staged = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, sql, params=None):
        s = sql.strip()
        if s.startswith("CREATE TABLE IF NOT EXISTS fullhistory_checkpoint"):
            self.db.setdefault("checkpoint", None)
        elif s.startswith("SELECT next_page, total_pages"):
            self._select_result = self.db.get("checkpoint")
        elif s.startswith("INSERT INTO fullhistory_checkpoint"):
            self.db["checkpoint"] = params
        elif s.startswith("DELETE FROM fullhistory_checkpoint"):
            self.db["checkpoint"] = None
        elif "CREATE TEMP TABLE" in s:
            self._staged = []
        elif s.startswith("INSERT INTO scrobbles"):
            existing = self.db.setdefault("scrobbles", set())
            before = len(existing)
            existing.update(self._staged)
            self.rowcount = len(existing) - before

    def fetchone(self):
        return self._select_result

    def copy(self, sql):
        return FakeCopy(self._staged)


class FakeConn:
    def __init__(self, db):
        self.db = db
        self.commits = 0

    def cursor(self):
        return FakeCursor(self.db)

    def commit(self):
        self.commits += 1

    def close(self):
        pass


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fh.time, "sleep", lambda s: None)


def test_fresh_run_fetches_all_pages_and_clears_checkpoint(monkeypatch):
    db = {}
    monkeypatch.setattr(fh, "_connect", lambda: FakeConn(db))

    calls = []

    def fake_request_page(params):
        page = params["page"]
        calls.append(page)
        return {"recenttracks": {"track": [make_track(page)], "@attr": {"totalPages": "3"}}}

    monkeypatch.setattr(fh, "_request_page", fake_request_page)

    fh.run_full_history()

    assert calls == [1, 2, 3]
    assert len(db["scrobbles"]) == 3
    assert db["checkpoint"] is None  # cleared on successful completion


def test_interrupted_run_resumes_from_checkpoint_on_a_new_connection(monkeypatch):
    db = {}
    monkeypatch.setattr(fh, "_connect", lambda: FakeConn(db))

    calls = []
    crashed_once = {"done": False}

    def fake_request_page(params):
        page = params["page"]
        calls.append(page)
        if page == 3 and not crashed_once["done"]:
            crashed_once["done"] = True
            raise SystemExit("simulated interruption")
        return {"recenttracks": {"track": [make_track(page)], "@attr": {"totalPages": "5"}}}

    monkeypatch.setattr(fh, "_request_page", fake_request_page)

    with pytest.raises(SystemExit):
        fh.run_full_history()

    assert db["checkpoint"] == (3, 5)
    assert len(db["scrobbles"]) == 2  # pages 1-2 already durably committed

    # A brand-new connection/process picks up where it left off.
    fh.run_full_history()

    assert len(db["scrobbles"]) == 5
    assert db["checkpoint"] is None
    assert calls == [1, 2, 3, 3, 4, 5]  # page 3 refetched, no data lost or skipped


def test_rejected_rows_are_not_loaded_but_do_not_stop_the_run(monkeypatch):
    db = {}
    monkeypatch.setattr(fh, "_connect", lambda: FakeConn(db))

    def fake_request_page(params):
        page = params["page"]
        if page == 1:
            track = make_track(1, artist="")  # invalid: missing artist
        else:
            track = make_track(page)
        return {"recenttracks": {"track": [track], "@attr": {"totalPages": "2"}}}

    monkeypatch.setattr(fh, "_request_page", fake_request_page)

    fh.run_full_history()

    assert len(db["scrobbles"]) == 1  # only the valid page-2 row was loaded
    assert db["checkpoint"] is None


def test_missing_recenttracks_key_raises_system_exit(monkeypatch):
    db = {}
    monkeypatch.setattr(fh, "_connect", lambda: FakeConn(db))
    monkeypatch.setattr(fh, "_request_page", lambda params: {"unexpected": "shape"})

    with pytest.raises(SystemExit):
        fh.run_full_history()