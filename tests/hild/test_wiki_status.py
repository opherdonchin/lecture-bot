"""Tests for the wiki staleness check (HILD/scripts/wiki_status.py)."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "HILD/scripts/wiki_status.py"
spec = importlib.util.spec_from_file_location("wiki_status", SCRIPT)
wiki_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wiki_status)


def run_git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


def page_text(status, covers="`code.py`", as_of="", kind="code"):
    return (
        "| | |\n|---|---|\n"
        f"| **Kind** | {kind} |\n| **Status** | {status} |\n"
        f"| **Covers** | {covers} |\n| **As of** | `{as_of}` |\n\n"
        "## What it does\n\nSomething.\n"
    )


@pytest.fixture
def repo(tmp_path):
    """A git repo with one code file, plus an empty wiki folder inside it."""
    run_git(tmp_path, "init", "-q")
    (tmp_path / "code.py").write_text("a = 1\n")
    run_git(tmp_path, "add", "code.py")
    run_git(tmp_path, "commit", "-qm", "first")
    (tmp_path / "wiki").mkdir()
    return tmp_path


def head(repo):
    return wiki_status.git(repo, "rev-parse", "--short", "HEAD").strip()


def change_code(repo, lines):
    (repo / "code.py").write_text("".join(f"x{i} = {i}\n" for i in range(lines)))
    run_git(repo, "commit", "-qam", "change")


def test_parse_header_reads_only_the_top_table():
    text = page_text("draft", as_of="abc1234") + "\n| **Status** | understood |\n"
    header = wiki_status.parse_header(text)
    assert header["status"] == "draft"
    assert header["as of"] == "`abc1234`"


def test_unchanged_code_is_not_stale(repo):
    (repo / "wiki/Code-thing.md").write_text(page_text("understood", as_of=head(repo)))
    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert page["changed"] == 0
    assert not page["stale"]


def test_small_change_stays_under_threshold(repo):
    (repo / "wiki/Code-thing.md").write_text(page_text("understood", as_of=head(repo)))
    change_code(repo, lines=3)  # 1 deleted + 3 added
    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert page["changed"] == 4
    assert not page["stale"]


def test_large_change_is_stale_and_write_marks_it(repo):
    wiki_page = repo / "wiki/Code-thing.md"
    wiki_page.write_text(page_text("understood", as_of=head(repo)))
    change_code(repo, lines=30)

    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert page["stale"]

    assert wiki_status.main(["--repo", str(repo), "--ref", "HEAD", "--write"]) == 0
    assert "| **Status** | stale |" in wiki_page.read_text()
    board = (repo / "wiki/Status-board.md").read_text()
    assert "## stale (1)" in board
    assert "[[Code-thing]]" in board


def test_deleted_file_makes_page_stale(repo):
    (repo / "wiki/Code-thing.md").write_text(page_text("draft", as_of=head(repo)))
    run_git(repo, "rm", "-q", "code.py")
    run_git(repo, "commit", "-qm", "remove")
    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert page["missing"] == ["code.py"]
    assert page["stale"]


def test_stub_pages_are_never_stale(repo):
    (repo / "wiki/Code-thing.md").write_text(page_text("stub", as_of=head(repo)))
    change_code(repo, lines=30)
    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert not page["stale"]


def test_concept_pages_are_listed_but_not_checked(repo):
    (repo / "wiki/Concept-idea.md").write_text(
        "| | |\n|---|---|\n| **Kind** | concept |\n| **Status** | draft |\n\nText.\n"
    )
    (page,) = wiki_status.read_pages(repo, repo / "wiki", threshold=10)
    assert page["changed"] is None
    assert not page["problem"]


def test_problems_are_reported(repo):
    (repo / "wiki/Code-no-header.md").write_text("Just text.\n")
    (repo / "wiki/Code-bad-commit.md").write_text(page_text("draft", as_of="deadbee"))
    (repo / "wiki/Code-bad-status.md").write_text(
        page_text("finished", as_of=head(repo))
    )
    pages = {p["name"]: p for p in wiki_status.read_pages(repo, repo / "wiki", 10)}
    assert pages["Code-no-header"]["problem"] == "no header table"
    assert "deadbee" in pages["Code-bad-commit"]["problem"]
    assert "unknown status" in pages["Code-bad-status"]["problem"]
    assert wiki_status.main(["--repo", str(repo), "--ref", "HEAD"]) == 1


def test_home_and_board_are_skipped(repo):
    (repo / "wiki/Home.md").write_text("Welcome.\n")
    (repo / "wiki/Status-board.md").write_text("old\n")
    assert wiki_status.read_pages(repo, repo / "wiki", threshold=10) == []


def test_linked_pages_that_do_not_exist_are_not_written(repo):
    wiki = repo / "wiki"
    (wiki / "Concept-a.md").write_text(
        page_text("draft", kind="concept")
        + "See [[Concept-b]], [[the missing one|Concept-c]] and [[Concept c]].\n"
    )
    (wiki / "Concept-b.md").write_text(
        page_text("draft", kind="concept") + "[[Concept-c]]\n"
    )
    (wiki / "Home.md").write_text("[[Concept-a]] [[Concept-d]]\n")
    missing = wiki_status.not_written(wiki)
    assert missing == {"Concept-c": ["Concept-a", "Concept-b"], "Concept-d": ["Home"]}
    pages = wiki_status.read_pages(repo, wiki, threshold=10)
    board = wiki_status.render_board(pages, "HEAD", head(repo), missing)
    assert "## not-written (2)" in board
    assert "| `Concept-c` | [[Concept-a]], [[Concept-b]] |" in board
    assert "not-written" in wiki_status.render_report(pages, missing)


def test_board_has_no_not_written_section_when_every_link_resolves(repo):
    wiki = repo / "wiki"
    (wiki / "Concept-a.md").write_text(
        page_text("needs-revision", kind="concept") + "[[Concept-a]]\n"
    )
    pages = wiki_status.read_pages(repo, wiki, threshold=10)
    assert not pages[0]["problem"]
    board = wiki_status.render_board(
        pages, "HEAD", head(repo), wiki_status.not_written(wiki)
    )
    assert "## needs-revision (1)" in board
    assert "not-written" not in board

def test_first_write_does_not_report_generated_board_as_missing(repo, capsys):
    wiki = repo / "wiki"
    (wiki / "Home.md").write_text("[[Status-board]]\n", encoding="utf-8")

    # Before generation, the reference really is missing.
    assert wiki_status.not_written(wiki) == {"Status-board": ["Home"]}
    assert wiki_status.main(["--repo", str(repo), "--ref", "HEAD", "--write"]) == 0

    board = (wiki / "Status-board.md").read_text(encoding="utf-8")
    assert "## not-written" not in board
    assert "not-written" not in capsys.readouterr().out
    assert wiki_status.not_written(wiki) == {}

def test_process_describes_the_same_reviewer_status_as_wiki_tool():
    process = (Path(__file__).parents[1] / "HILD/process.md").read_text(encoding="utf-8")
    assert "| `understood` | reviewer only |" in process
    assert "| `hild-understood` |" not in process
    assert "understood" in wiki_status.STATUSES
