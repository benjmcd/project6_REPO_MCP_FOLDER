"""Version-robust enumeration of an app's registered routes.

Why this exists: FastAPI changed `include_router` semantics around 0.115. Older
versions flattened a sub-router's routes directly into the parent's
`app.router.routes`, so naive iteration found every route. Newer versions
(>=0.115 / Starlette 1.x) insert a lazy `_IncludedRouter` node instead, so
`app.router.routes` exposes the included routes only behind that node — naive
`for r in app.router.routes` finds zero of them. The app still *serves* every
route (OpenAPI and request dispatch are unaffected); only direct introspection
breaks.

`iter_api_routes` handles both layouts: it asks an `_IncludedRouter` for its
resolved route contexts (which carry the fully-prefixed path and the endpoint),
and otherwise reads the route directly and descends into mounted sub-apps. The
result matches `app.openapi()` exactly on both fastapi 0.111 and 0.137.
"""
from __future__ import annotations

from typing import Any


def iter_api_routes(app: Any) -> list[tuple[str, set[str], Any]]:
    """Return [(full_path, methods, endpoint)] for every concrete route on app,
    robust to the fastapi include_router flattening change."""
    out: list[tuple[str, set[str], Any]] = []
    seen: set[tuple[str, frozenset[str], int]] = set()

    def emit(path: Any, methods: Any, endpoint: Any) -> None:
        if not (path and methods and endpoint):
            return
        key = (str(path), frozenset(methods), id(endpoint))
        if key in seen:
            return
        seen.add(key)
        out.append((str(path), set(methods), endpoint))

    def visit(routes: Any) -> None:
        for route in routes or ():
            # fastapi >=0.115: included routers expose resolved contexts that
            # already carry the fully-prefixed path and the endpoint.
            # NOTE: effective_route_contexts is a fastapi internal (no public
            # equivalent exposes the endpoint object). If a future fastapi drops
            # or renames it, this branch is skipped, discovery returns [], and the
            # callers' `assert discovered` / OpenAPI cross-check fail loudly rather
            # than silently shrinking — see the coverage guard tests.
            resolved = getattr(route, "effective_route_contexts", None)
            if callable(resolved):
                for ctx in resolved():
                    emit(
                        getattr(ctx, "path", None),
                        getattr(ctx, "methods", None),
                        getattr(ctx, "endpoint", None),
                    )
                continue
            # Flat APIRoute/Route (older fastapi, or routes defined directly).
            emit(
                getattr(route, "path", None),
                getattr(route, "methods", None),
                getattr(route, "endpoint", None),
            )
            # Descend into mounted sub-apps (e.g. StaticFiles mounts).
            sub = getattr(getattr(route, "app", None), "routes", None)
            if sub:
                visit(sub)

    visit(getattr(app.router, "routes", []))
    return out


def post_routes(app: Any) -> list[tuple[str, Any]]:
    """[(full_path, endpoint)] for every registered POST route."""
    return [(path, endpoint) for path, methods, endpoint in iter_api_routes(app) if "POST" in methods]
