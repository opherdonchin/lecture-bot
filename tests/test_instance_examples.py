"""Checks on the committed course-instance deployment examples."""

import pathlib as pathlib_

import app.config as config_module

REPO_ROOT = pathlib_.Path(__file__).resolve().parent.parent
PML_ENV_EXAMPLE = REPO_ROOT / "deploy" / "instances" / "pml.env.example"
PML_ROOT = "/srv/lecture-bot-instances/pml/"


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


def _setting_env_names() -> set[str]:
    """Return the environment variable name of every app setting."""
    names = set()
    for field_name, field in config_module.Settings.model_fields.items():
        alias = field.validation_alias
        names.add(alias if isinstance(alias, str) else field_name.upper())
    return names


def test_pml_env_example_sets_every_setting():
    # A setting left out would silently fall back to the checkout's .env,
    # which belongs to Statistics.
    values = _read_env_example(PML_ENV_EXAMPLE)

    missing = _setting_env_names() - set(values)

    assert missing == set()


def test_pml_env_example_paths_stay_inside_the_pml_instance():
    values = _read_env_example(PML_ENV_EXAMPLE)
    path_keys = [key for key in values if key == "LECTURES_DIR" or key.startswith("MOODLE_") and key.endswith(("_DIR", "_CSV"))]

    assert path_keys
    for key in path_keys:
        assert values[key].startswith(PML_ROOT), key
    assert values["DATABASE_URL"] == f"sqlite:///{PML_ROOT}data/lecture_bot.db"


def test_pml_env_example_uses_its_own_ports_paths_and_service():
    values = _read_env_example(PML_ENV_EXAMPLE)

    assert values["LECTURE_BOT_STUDENT_ROOT_PATH"] == "/pml"
    assert values["LECTURE_BOT_ADMIN_ROOT_PATH"] == "/pml-admin"
    assert (values["LECTURE_BOT_STUDENT_PORT"], values["LECTURE_BOT_ADMIN_PORT"]) == ("8002", "8003")
    assert values["STUDENT_RESTART_COMMAND"].endswith("restart lecture-bot@pml.service")
