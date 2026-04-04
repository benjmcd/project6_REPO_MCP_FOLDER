from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings


def test_settings_reads_db_init_mode_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DB_INIT_MODE= NONE \n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.db_init_mode == "none"


def test_settings_defaults_db_init_mode_to_migrate_without_env_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_INIT_MODE", raising=False)

    settings = Settings(_env_file=None)

    assert settings.db_init_mode == "migrate"


def test_settings_reject_invalid_db_init_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_INIT_MODE", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("DB_INIT_MODE=launch_all_the_tables\n", encoding="utf-8")

    with pytest.raises(ValueError, match="DB_INIT_MODE must be one of"):
        Settings(_env_file=env_file)


def test_main_uses_settings_db_init_mode_instead_of_direct_env_reads() -> None:
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    main_source = main_path.read_text(encoding="utf-8")

    assert "settings.db_init_mode" in main_source
    assert 'os.getenv("DB_INIT_MODE"' not in main_source
    assert "load_dotenv" not in main_source
