import json as j
import pathlib as pathlib_

import pytest

import scripts.lecture_package as lecture_package


BRIEF = """# Lecture brief: Fixture

## Lecture at a glance
- **Load-bearing:** T2.

### T1. Framing

### T2. Core result
"""


def make_instance(root: pathlib_.Path, *, active: bool = False, rubric: str = BRIEF, topics=None, package_contract: str | None = "pml-brief-1") -> pathlib_.Path:
    """Create <root>/pml/lectures/lecture_02 with a brief, bot notes and an unused source."""
    lectures = root / "pml" / "lectures"
    lecture_dir = lectures / "lecture_02"
    lecture_dir.mkdir(parents=True)
    (lectures / "config.json").write_text(
        j.dumps({"context_files": [{"key": "bot_notes", "path": "bot_notes.md", "required": True}]}),
        encoding="utf-8",
    )
    config = {"lecture_id": "lecture_02", "title": "Lecture 2", "active": active}
    if topics is not None:
        config["topics"] = topics
    if package_contract is not None:
        config["package_contract"] = package_contract
    (lecture_dir / "lecture_config.json").write_text(j.dumps(config), encoding="utf-8")
    (lecture_dir / "rubric.md").write_text(rubric, encoding="utf-8")
    (lecture_dir / "bot_notes.md").write_text("Notes\n", encoding="utf-8")
    (lecture_dir / "slides.md").write_text("Not installed\n", encoding="utf-8")
    return lecture_dir


def test_check_passes_and_lists_only_runtime_files(tmp_path):
    result = lecture_package.check_lecture(make_instance(tmp_path))

    assert result.ok, result.errors
    assert result.files == ["lecture_config.json", "rubric.md", "bot_notes.md"]
    assert [t["topic_id"] for t in result.topics] == ["T1", "T2"]
    assert result.load_bearing == ["- **Load-bearing:** T2."]


def test_check_fails_without_rubric(tmp_path):
    lecture_dir = make_instance(tmp_path)
    (lecture_dir / "rubric.md").unlink()

    result = lecture_package.check_lecture(lecture_dir)

    assert not result.ok
    assert "rubric.md" in result.errors[0]


def test_check_fails_without_topics(tmp_path):
    no_topics = lecture_package.check_lecture(make_instance(tmp_path, rubric="# Brief\n"))

    assert any("topic headings" in error for error in no_topics.errors)


def test_check_reports_the_package_contract(tmp_path):
    result = lecture_package.check_lecture(make_instance(tmp_path))

    assert result.package_contract == "pml-brief-1"
    assert "Package contract: pml-brief-1" in lecture_package.format_check(result)


@pytest.mark.parametrize("declared", ["pml-brief-0", None])
def test_check_fails_when_the_package_contract_differs_from_the_prompts(tmp_path, declared):
    result = lecture_package.check_lecture(make_instance(tmp_path, package_contract=declared))

    assert not result.ok
    assert any("pml-brief-1" in error and "pml_tutor_prompt.md" in error for error in result.errors)


def test_check_fails_for_a_course_without_a_declared_contract(tmp_path):
    lecture_dir = make_instance(tmp_path)
    renamed = tmp_path / "statistics"
    (tmp_path / "pml").rename(renamed)

    result = lecture_package.check_lecture(renamed / "lectures" / lecture_dir.name)

    assert any("declares no lecture package contract" in error for error in result.errors)


def test_check_uses_a_lectures_own_tutor_prompt(tmp_path):
    lecture_dir = make_instance(tmp_path)
    config_path = lecture_dir / "lecture_config.json"
    config = j.loads(config_path.read_text())
    config["tutor_prompt_template"] = "tutor_prompt.md"
    config_path.write_text(j.dumps(config), encoding="utf-8")

    result = lecture_package.check_lecture(lecture_dir)

    assert any("tutor_prompt.md declares no lecture package contract" in error for error in result.errors)


def test_check_fails_when_the_declared_contract_has_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(lecture_package, "PACKAGE_CONTRACTS_DIR", tmp_path / "no_contracts")

    result = lecture_package.check_lecture(make_instance(tmp_path))

    assert any("has no file" in error for error in result.errors)


def test_check_fails_for_an_unknown_course(tmp_path):
    lecture_dir = make_instance(tmp_path)
    renamed = tmp_path / "nosuchcourse"
    (tmp_path / "pml").rename(renamed)

    result = lecture_package.check_lecture(renamed / "lectures" / lecture_dir.name)

    assert any("Cannot find the tutor prompt" in error for error in result.errors)


def test_check_fails_when_config_topics_override_the_brief(tmp_path):
    stale = [{"topic_id": "T1", "label": "Old topic", "importance": "core"}]

    result = lecture_package.check_lecture(make_instance(tmp_path, topics=stale))

    assert not result.ok
    assert any("differ from rubric.md" in error for error in result.errors)


def push(tmp_path, target, **kwargs) -> int:
    return lecture_package.push_lecture(
        "pml", "lecture_02", instances_root=tmp_path, target_dir=target, env={}, **kwargs
    )


def test_push_installs_runtime_files_inactive(tmp_path):
    make_instance(tmp_path, active=True)
    target = tmp_path / "server" / "lectures"
    target.mkdir(parents=True)

    assert push(tmp_path, target) == 0

    installed = target / "lecture_02"
    assert sorted(p.name for p in installed.iterdir()) == ["bot_notes.md", "lecture_config.json", "rubric.md"]
    assert j.loads((installed / "lecture_config.json").read_text())["active"] is False
    assert [p.name for p in target.iterdir()] == ["lecture_02"]


def test_push_dry_run_installs_nothing(tmp_path):
    make_instance(tmp_path)
    target = tmp_path / "server" / "lectures"
    target.mkdir(parents=True)

    assert push(tmp_path, target, dry_run=True) == 0
    assert list(target.iterdir()) == []


def test_push_refuses_to_overwrite_without_replace_and_backs_up_with_it(tmp_path):
    make_instance(tmp_path)
    target = tmp_path / "server" / "lectures"
    target.mkdir(parents=True)
    assert push(tmp_path, target) == 0

    assert push(tmp_path, target) != 0
    assert push(tmp_path, target, replace=True) == 0
    backups = list((tmp_path / "server" / "lecture_backups").iterdir())
    assert len(backups) == 1 and backups[0].name.startswith("lecture_02-")


def test_push_never_replaces_an_active_lecture(tmp_path):
    make_instance(tmp_path)
    target = tmp_path / "server" / "lectures"
    (target / "lecture_02").mkdir(parents=True)
    (target / "lecture_02" / "lecture_config.json").write_text(j.dumps({"active": True}), encoding="utf-8")

    assert push(tmp_path, target, replace=True) != 0
    assert j.loads((target / "lecture_02" / "lecture_config.json").read_text())["active"] is True


def test_push_treats_a_lecture_with_no_active_setting_as_active(tmp_path):
    make_instance(tmp_path)
    target = tmp_path / "server" / "lectures"
    (target / "lecture_02").mkdir(parents=True)
    (target / "lecture_02" / "lecture_config.json").write_text(j.dumps({"title": "Old"}), encoding="utf-8")

    assert push(tmp_path, target, replace=True) != 0
    assert j.loads((target / "lecture_02" / "lecture_config.json").read_text()) == {"title": "Old"}


def test_push_refuses_a_failing_package(tmp_path):
    lecture_dir = make_instance(tmp_path)
    (lecture_dir / "bot_notes.md").unlink()
    target = tmp_path / "server" / "lectures"
    target.mkdir(parents=True)

    assert push(tmp_path, target) == 1
    assert list(target.iterdir()) == []


def test_ssh_command_uses_remote_settings():
    env = {"LECTURE_BOT_REMOTE_HOST": "example.org", "LECTURE_BOT_REMOTE_USER": "ops", "LECTURE_BOT_SSH_OPTS": "-p 2222"}

    assert lecture_package.push_command(env, None) == ["ssh", "-p", "2222", "ops@example.org"]
    with pytest.raises(SystemExit):
        lecture_package.push_command({}, None)
