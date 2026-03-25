import ast
import pathlib
import importlib

def _repo_root() -> pathlib.Path:
    # Assuming this file is at <repo>/tests/<this_file>.py
    return pathlib.Path(__file__).resolve().parents[1]


def test_no_backend_app_imports():
    """Fail if any source file imports ``backend.app`` or a submodule thereof.

    This guards against accidental drift toward the alternate import path that would
    create a second copy of the package and duplicate global state.
    """
    root = _repo_root()
    for py_path in root.rglob('*.py'):
        # Skip hidden directories (e.g., .venv, .git) and the virtual env site‑packages
        if any(part.startswith('.') for part in py_path.parts):
            continue
        # Skip the virtual‑environment directory if present under the repo
        if 'site-packages' in py_path.parts:
            continue
        source = py_path.read_text(encoding='utf-8')
        try:
            tree = ast.parse(source, filename=str(py_path))
        except SyntaxError:
            # If a file cannot be parsed (unlikely in this repo) we just ignore it.
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == 'backend.app' or name.startswith('backend.app.'):
                        raise AssertionError(f"Forbidden import of '{name}' in {py_path}")
            elif isinstance(node, ast.ImportFrom):
                # Absolute import from a module
                if node.module and (node.module == 'backend.app' or node.module.startswith('backend.app.')):
                    raise AssertionError(f"Forbidden import from '{node.module}' in {py_path}")


def test_app_imports_work():
    """Smoke test that the canonical ``app.*`` imports resolve correctly."""
    import sys, pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    modules = [
        'app.core.config',
        'app.db.session',
        'app.services.nrc_aps_evidence_bundle_gate',
    ]
    import sys
    print('sys.path during test:', sys.path)
    for name in modules:
        mod = importlib.import_module(name)
        assert mod is not None
