import app.root_path as root_path_module


def test_strip_redundant_root_path_removes_one_copy_of_a_duplicated_prefix():
    scope = {
        "type": "http",
        "root_path": "/bot",
        "path": "/bot/bot/health",
        "raw_path": b"/bot/bot/health",
    }

    updated = root_path_module.strip_redundant_root_path(scope)

    assert updated["path"] == "/bot/health"
    assert updated["raw_path"] == b"/bot/health"
    assert updated["root_path"] == "/bot"


def test_strip_redundant_root_path_keeps_single_prefix_request():
    scope = {
        "type": "http",
        "root_path": "/bot",
        "path": "/bot/health",
        "raw_path": b"/bot/health",
    }

    updated = root_path_module.strip_redundant_root_path(scope)

    assert updated is scope


def test_strip_redundant_root_path_does_not_strip_partial_prefix_match():
    scope = {
        "type": "http",
        "root_path": "/bot",
        "path": "/bot/botanical",
        "raw_path": b"/bot/botanical",
    }

    updated = root_path_module.strip_redundant_root_path(scope)

    assert updated is scope
