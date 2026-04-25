import pathlib

import app.db as db_module


def test_sqlite_file_path_preserves_relative_and_absolute_urls():
    assert db_module._sqlite_file_path("sqlite:///data/lecture_bot.db") == pathlib.Path("data/lecture_bot.db")
    assert db_module._sqlite_file_path("sqlite:////tmp/lecture_bot.db") == pathlib.Path("/tmp/lecture_bot.db")
    assert db_module._sqlite_file_path("sqlite:///:memory:") is None


def test_ensure_sqlite_parent_dir_creates_missing_relative_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    db_module._ensure_sqlite_parent_dir("sqlite:///nested/data/test.db")

    assert (tmp_path / "nested" / "data").is_dir()
