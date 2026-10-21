"""Checks on the committed course-instance environment examples.

Every file in deploy/instances/ describes one course instance. These tests hold
for all of them, so adding a course's example tests it against the others.
"""

import itertools as itertools_
import pathlib as pathlib_

import pytest

import app.config as config_module

REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
INSTANCE_EXAMPLES = sorted((REPO_ROOT / "deploy" / "instances").glob("*.env.example"))
INSTANCES_ROOT = "/srv/lecture-bot/instances"
PATH_KEYS_PREFIXES = ("LECTURES_DIR", "MOODLE_")
PATH_KEY_SUFFIXES = ("_DIR", "_CSV")


def _read_env_example(path: pathlib_.Path) -> dict[str, str]:
    """Return the KEY=value assignments in an env example file."""
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key] = value
    return values


def _instance_name(path: pathlib_.Path) -> str:
    """Return the instance name, which is the file name before .env.example."""
    return path.name.removesuffix(".env.example")


def _setting_env_names() -> set[str]:
    """Return the environment variable name of every app setting."""
    names = set()
    for field_name, field in config_module.Settings.model_fields.items():
        alias = field.validation_alias
        names.add(alias if isinstance(alias, str) else field_name.upper())
    return names


def _instance_paths(values: dict[str, str]) -> dict[str, str]:
    """Return the filesystem paths an instance's settings point to."""
    paths = {
        key: value
        for key, value in values.items()
        if key.startswith(PATH_KEYS_PREFIXES) and key.endswith(PATH_KEY_SUFFIXES)
    }
    paths["DATABASE_URL"] = values["DATABASE_URL"].removeprefix("sqlite:///")
    return paths


def _claims(path: pathlib_.Path) -> dict[str, str]:
    """Return what an instance must not share with any other instance."""
    values = _read_env_example(path)
    return {
        "folder": f"{INSTANCES_ROOT}/{_instance_name(path)}",
        "student port": values["LECTURE_BOT_STUDENT_PORT"],
        "admin port": values["LECTURE_BOT_ADMIN_PORT"],
        "student path": values["LECTURE_BOT_STUDENT_ROOT_PATH"],
        "admin path": values["LECTURE_BOT_ADMIN_ROOT_PATH"],
        "admin username": values["ADMIN_USERNAME"],
        "restart command": values["STUDENT_RESTART_COMMAND"],
    }


def test_there_are_instance_examples():
    assert len(INSTANCE_EXAMPLES) >= 2


@pytest.mark.parametrize("path", INSTANCE_EXAMPLES, ids=_instance_name)
def test_instance_example_sets_every_setting(path):
    # The checkout has no .env, so a setting left out would fall back to a
    # default inside the shared checkout rather than inside the instance.
    missing = _setting_env_names() - set(_read_env_example(path))

    assert missing == set()


@pytest.mark.parametrize("path", INSTANCE_EXAMPLES, ids=_instance_name)
def test_instance_example_paths_stay_inside_its_own_folder(path):
    folder = f"{INSTANCES_ROOT}/{_instance_name(path)}/"

    outside = {key: value for key, value in _instance_paths(_read_env_example(path)).items() if not value.startswith(folder)}

    assert outside == {}


@pytest.mark.parametrize("path", INSTANCE_EXAMPLES, ids=_instance_name)
def test_instance_example_restarts_its_own_service(path):
    values = _read_env_example(path)

    assert values["STUDENT_RESTART_COMMAND"].endswith(f"restart lecture-bot@{_instance_name(path)}.service")


@pytest.mark.parametrize(
    "first,second",
    list(itertools_.combinations(INSTANCE_EXAMPLES, 2)),
    ids=lambda path: _instance_name(path),
)
def test_instance_examples_share_nothing(first, second):
    first_claims = _claims(first)
    second_claims = _claims(second)
    all_first_values = set(first_claims.values())

    shared = {kind: value for kind, value in second_claims.items() if value in all_first_values}

    assert shared == {}
