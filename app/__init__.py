"""Top-level alias package to expose the backend.app package as `app`.

This file adjusts ``sys.path`` so that imports such as ``import app.models``
resolve to the actual package located at ``backend/app``.
"""
import sys
import pathlib

# Determine the absolute path to the real backend/app package (project root -> backend/app)
_backend_path = pathlib.Path(__file__).resolve().parents[1] / "backend" / "app"
_backend_path_str = str(_backend_path)

# Ensure the path is on sys.path (prepend to give it priority)
if _backend_path_str not in sys.path:
    sys.path.insert(0, _backend_path_str)

# Make this package a namespace package that points to the backend implementation
__path__ = [_backend_path_str]
