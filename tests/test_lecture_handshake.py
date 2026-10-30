import io as io_module
import json as j
import pathlib as pathlib_
import stat as stat_module
import zipfile as zipfile_module

import pytest

import app.lecture_packages as lecture_packages
import scripts.lecture_package_server as server


BRIEF = "# Brief\n\n## Lecture at a glance\n- **Load-bearing:** T2.\n\n### T1. Framing\n\n### T2. Core result\n"
PROMPT = "pml_tutor_prompt.md"


def make_archive(files: dict[str, str] | None = None, **config_overrides) -> bytes:
    config = {"title": "Lecture 3", "package_contract": "pml-brief-1", "active": True, **config_overrides}
    contents = {"lecture_config.json": j.dumps(config), "rubric.md": BRIEF, "bot_notes.md": "Notes\n"}
    contents.update(files or {})
    buffer = io_module.BytesIO()
    with zipfile_module.ZipFile(buffer, "w") as archive:
        for name, content in contents.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture
def lectures_dir(tmp_path) -> pathlib_.Path:
    lectures = tmp_path / "pml" / "lectures"
    lectures.mkdir(parents=True)
    (lectures / "config.json").write_text(
        j.dumps({"context_files": [{"key": "bot_notes", "path": "bot_notes.md", "required": True}]}),
        encoding="utf-8",
    )
    return lectures


def test_check_archive_gives_the_documented_result_and_installs_nothing(lectures_dir):
    result = lecture_packages.check_archive(lectures_dir, "lecture_03", make_archive(), PROMPT).to_dict()

    assert result == {
        "handshake": 1,
        "ok": True,
        "lecture_id": "lecture_03",
        "package_contract": "pml-brief-1",
        "files": ["lecture_config.json", "rubric.md", "bot_notes.md"],
        "topics": [{"topic_id": "T1", "label": "Framing"}, {"topic_id": "T2", "label": "Core result"}],
        "load_bearing": ["- **Load-bearing:** T2."],
        "errors": [],
        "installed": False,
        "message": "",
    }
    assert [path.name for path in lectures_dir.iterdir()] == ["config.json"]


def test_install_always_switches_the_lecture_off_and_sets_modes(lectures_dir):
    result = lecture_packages.install_archive(lectures_dir, "lecture_03", make_archive(), PROMPT)

    assert result.ok and result.installed
    installed = lectures_dir / "lecture_03"
    assert j.loads((installed / "lecture_config.json").read_text())["active"] is False
    assert stat_module.S_IMODE(installed.stat().st_mode) == 0o2770
    assert stat_module.S_IMODE((installed / "rubric.md").stat().st_mode) == 0o660
    assert not [path for path in lectures_dir.iterdir() if path.name.startswith(".")]


def test_install_refuses_an_existing_lecture_unless_asked_and_then_backs_it_up(lectures_dir):
    assert lecture_packages.install_archive(lectures_dir, "lecture_03", make_archive(), PROMPT).ok

    refused = lecture_packages.install_archive(lectures_dir, "lecture_03", make_archive(), PROMPT)
    assert not refused.installed and "already installed" in refused.errors[0]

    replaced = lecture_packages.install_archive(lectures_dir, "lecture_03", make_archive(), PROMPT, replace=True)
    assert replaced.installed
    backups = list((lectures_dir.parent / "lecture_backups").iterdir())
    assert len(backups) == 1 and backups[0].name.startswith("lecture_03-")


@pytest.mark.parametrize("old_config", [{"active": True}, {"title": "No active setting"}])
def test_install_never_replaces_a_lecture_that_is_not_marked_off(lectures_dir, old_config):
    existing = lectures_dir / "lecture_03"
    existing.mkdir()
    (existing / "lecture_config.json").write_text(j.dumps(old_config), encoding="utf-8")

    result = lecture_packages.install_archive(lectures_dir, "lecture_03", make_archive(), PROMPT, replace=True)

    assert not result.installed and "not marked as off" in result.errors[0]
    assert j.loads((existing / "lecture_config.json").read_text()) == old_config


def test_a_package_for_another_contract_is_not_installed(lectures_dir):
    archive = make_archive(package_contract="pml-brief-0")

    result = lecture_packages.install_archive(lectures_dir, "lecture_03", archive, PROMPT)

    assert not result.installed and "pml-brief-1" in result.errors[0]
    assert not (lectures_dir / "lecture_03").exists()


def test_files_the_app_does_not_read_are_refused(lectures_dir):
    result = lecture_packages.check_archive(
        lectures_dir, "lecture_03", make_archive({"transcript.md": "Private\n"}), PROMPT
    )

    assert any("transcript.md" in error for error in result.errors)


@pytest.mark.parametrize("name", ["../escape.md", "sub/rubric.md", "/absolute.md", "back\\slash.md"])
def test_unsafe_archive_paths_are_refused(lectures_dir, name):
    buffer = io_module.BytesIO()
    with zipfile_module.ZipFile(buffer, "w") as archive:
        archive.writestr(name, "x")

    result = lecture_packages.install_archive(lectures_dir, "lecture_03", buffer.getvalue(), PROMPT)

    assert not result.installed and "top level" in result.errors[0]
    assert not (lectures_dir.parent / "escape.md").exists()


def test_a_symlink_in_an_archive_is_refused(lectures_dir):
    buffer = io_module.BytesIO()
    with zipfile_module.ZipFile(buffer, "w") as archive:
        info = zipfile_module.ZipInfo("rubric.md")
        info.external_attr = (stat_module.S_IFLNK | 0o777) << 16
        archive.writestr(info, "/etc/passwd")

    result = lecture_packages.check_archive(lectures_dir, "lecture_03", buffer.getvalue(), PROMPT)

    assert "top level" in result.errors[0]


def test_something_other_than_a_zip_is_refused(lectures_dir):
    result = lecture_packages.check_archive(lectures_dir, "lecture_03", b"not a zip", PROMPT)

    assert "not a valid .zip" in result.errors[0]


def test_an_oversized_archive_is_refused(lectures_dir, monkeypatch):
    monkeypatch.setattr(lecture_packages, "MAX_ARCHIVE_BYTES", 10)

    result = lecture_packages.check_archive(lectures_dir, "lecture_03", make_archive(), PROMPT)

    assert "larger than" in result.errors[0]


@pytest.mark.parametrize("lecture_id", ["../lecture_03", "a/b", "", ".."])
def test_unsafe_lecture_ids_are_refused(lectures_dir, lecture_id):
    result = lecture_packages.install_archive(lectures_dir, lecture_id, make_archive(), PROMPT)

    assert not result.installed and "not a valid lecture id" in result.errors[0]


def test_a_config_that_is_not_an_object_is_refused(lectures_dir):
    archive = make_archive({"lecture_config.json": "[1, 2]"})

    result = lecture_packages.check_archive(lectures_dir, "lecture_03", archive, PROMPT)

    assert "cannot be loaded" in result.errors[0]


def test_describe_expectations_gives_the_contract_rules_and_instructions():
    response = lecture_packages.describe_expectations(PROMPT)

    assert response["ok"] and response["handshake"] == 1
    assert response["package_contract"] == "pml-brief-1"
    assert "pml-brief-1" in response["contract"]
    assert "What makes a contract valid" in response["shared_rules"]
    assert "lecture_recipe.md" in response["instructions"]


def test_describe_expectations_reports_a_prompt_without_a_contract():
    response = lecture_packages.describe_expectations("tutor_prompt.md")

    assert not response["ok"] and "declares no lecture package contract" in response["errors"][0]


@pytest.fixture
def instance(tmp_path, lectures_dir, monkeypatch) -> pathlib_.Path:
    (tmp_path / "pml" / "instance.env").write_text(
        f'ADMIN_PASSWORD=do-not-print\nLECTURES_DIR="{lectures_dir}"\nTUTOR_PROMPT_TEMPLATE={PROMPT}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("LECTURE_BOT_INSTANCES_ROOT", str(tmp_path))
    return lectures_dir


def test_the_server_command_reads_only_the_settings_it_needs(instance, capsys):
    assert server.instance_settings("pml") == (instance, PROMPT)
    assert server.main(["contract", "pml"]) == 0
    output = capsys.readouterr().out
    assert "do-not-print" not in output
    assert j.loads(output)["package_contract"] == "pml-brief-1"


def test_the_server_command_installs_from_stdin(instance, capsys, monkeypatch):
    class FakeStdin:
        buffer = io_module.BytesIO(make_archive())

    monkeypatch.setattr(server.sys_module, "stdin", FakeStdin)

    assert server.main(["install", "pml", "lecture_03"]) == 0
    assert j.loads(capsys.readouterr().out)["installed"] is True
    assert (instance / "lecture_03" / "rubric.md").exists()


@pytest.mark.parametrize("course", ["nosuchcourse", "../pml"])
def test_the_server_command_reports_a_bad_course(instance, capsys, course):
    assert server.main(["contract", course]) == 1
    assert j.loads(capsys.readouterr().out)["ok"] is False


def test_the_server_command_exits_nonzero_when_a_check_fails(instance, capsys, monkeypatch):
    class FakeStdin:
        buffer = io_module.BytesIO(b"not a zip")

    monkeypatch.setattr(server.sys_module, "stdin", FakeStdin)

    assert server.main(["check", "pml", "lecture_03"]) == 1
    assert j.loads(capsys.readouterr().out)["ok"] is False
