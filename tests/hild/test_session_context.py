"""Regression checks for the HILD startup context shell collector."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "HILD/scripts/session_context.sh"


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test",
         "-c", "user.email=test@example.org", *args],
        text=True, check=True, capture_output=True,
    ).stdout.strip()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash unavailable")
def test_startup_reports_commits_since_latest_hild_journal(tmp_path):
    repo = tmp_path / "project"
    repo.mkdir()
    git(repo, "init", "-q")
    journal = repo / "HILD/journal/2026-10-18.md"
    journal.parent.mkdir(parents=True)
    journal.write_text("# Journal\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Record first journal")

    (repo / "feature.py").write_text("value = 1\n", encoding="utf-8")
    git(repo, "add", "feature.py")
    git(repo, "commit", "-qm", "Code milestone after journal")

    # Stub gh so the test is independent of network and user credentials.
    stub_dir = tmp_path / "tools"
    stub_dir.mkdir()
    gh = stub_dir / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    gh.chmod(0o755)
    env = dict(os.environ, PATH=str(stub_dir) + os.pathsep + os.environ["PATH"])

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--- Latest journal entry: HILD/journal/2026-10-18.md ---" in result.stdout
    assert "Code milestone after journal" in result.stdout

@pytest.mark.skipif(shutil.which("bash") is None, reason="bash unavailable")
def test_startup_does_not_pull_remote_wiki_changes(tmp_path):
    """Orientation can inspect a local wiki, but must not modify its Git state."""
    repo = tmp_path / "project"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "README.md").write_text("# Project\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Initial project")

    bare = tmp_path / "wiki.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    seed = tmp_path / "wiki-seed"
    seed.mkdir()
    git(seed, "init", "-q")
    git(seed, "remote", "add", "origin", str(bare))
    (seed / "Home.md").write_text("Version one\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-qm", "Initial wiki")
    git(seed, "push", "-q", "-u", "origin", "HEAD")

    wiki = repo / "wiki"
    subprocess.run(["git", "clone", "-q", str(bare), str(wiki)], check=True)
    original_head = git(wiki, "rev-parse", "HEAD")
    (seed / "Home.md").write_text("Version two\n", encoding="utf-8")
    git(seed, "commit", "-qam", "Remote wiki edit")
    git(seed, "push", "-q")
    assert git(seed, "rev-parse", "HEAD") != original_head

    result = subprocess.run(
        ["bash", str(SCRIPT)], cwd=repo, text=True,
        capture_output=True, timeout=30,
        env=dict(os.environ, PATH=os.environ["PATH"]),
    )
    assert result.returncode == 0, result.stderr
    assert git(wiki, "rev-parse", "HEAD") == original_head
    assert (wiki / "Home.md").read_text(encoding="utf-8") == "Version one\n"
    assert "remote changes were not fetched" in result.stdout
