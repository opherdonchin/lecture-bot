from __future__ import annotations

from collections.abc import Awaitable, Callable


ASGIApp = Callable[[dict, Callable[[], Awaitable[dict]], Callable[[dict], Awaitable[None]]], Awaitable[None]]


def _normalize_root_path(value: str) -> str:
    if not value or value == "/":
        return ""
    return value.rstrip("/")


def _configured_root_path(scope: dict, fallback_root_path: str = "") -> str:
    scope_root_path = scope.get("root_path", "")
    if isinstance(scope_root_path, str) and scope_root_path:
        return scope_root_path

    app = scope.get("app")
    app_root_path = getattr(app, "root_path", "")
    if isinstance(app_root_path, str) and app_root_path:
        return app_root_path

    return fallback_root_path


def strip_redundant_root_path(scope: dict, fallback_root_path: str = "") -> dict:
    """Collapse duplicate root_path prefixes from direct Uvicorn requests."""
    if scope.get("type") not in {"http", "websocket"}:
        return scope

    root_path = _normalize_root_path(_configured_root_path(scope, fallback_root_path))
    if not root_path:
        return scope

    path = scope.get("path", "")
    duplicated_root_path = f"{root_path}{root_path}"
    if path == duplicated_root_path:
        stripped_path = root_path
    elif path.startswith(f"{duplicated_root_path}/"):
        stripped_path = path[len(root_path):] or "/"
    else:
        return scope

    updated_scope = dict(scope)
    updated_scope["path"] = stripped_path

    raw_path = scope.get("raw_path")
    if isinstance(raw_path, bytes):
        raw_root_path = root_path.encode("utf-8")
        duplicated_raw_root_path = raw_root_path + raw_root_path
        if raw_path == duplicated_raw_root_path:
            updated_scope["raw_path"] = raw_root_path
        elif raw_path.startswith(duplicated_raw_root_path + b"/"):
            updated_scope["raw_path"] = raw_path[len(raw_root_path):] or b"/"

    return updated_scope


class RootPathStripMiddleware:
    def __init__(self, app: ASGIApp, configured_root_path: str = ""):
        self.app = app
        self.configured_root_path = configured_root_path

    async def __call__(self, scope, receive, send):
        await self.app(
            strip_redundant_root_path(scope, self.configured_root_path),
            receive,
            send,
        )
