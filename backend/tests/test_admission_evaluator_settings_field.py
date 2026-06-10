"""Tests for sec_xbrl_production_admission_evaluator_enabled settings field
and its integration into production_admission_flag_enabled()."""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.services.layer3_sec_xbrl_production_admission import production_admission_flag_enabled


def test_default_false(monkeypatch) -> None:
    """Field defaults to False; flag returns False when no env set."""
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)
    monkeypatch.setattr(settings, "sec_xbrl_production_admission_evaluator_enabled", False)
    assert settings.sec_xbrl_production_admission_evaluator_enabled is False
    assert production_admission_flag_enabled() is False


def test_env_truthy_enables_flag(monkeypatch) -> None:
    """Setting env var to '1' makes production_admission_flag_enabled() return True."""
    monkeypatch.setattr(settings, "sec_xbrl_production_admission_evaluator_enabled", False)
    monkeypatch.setenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", "1")
    assert production_admission_flag_enabled() is True


def test_settings_attr_true_enables_flag(monkeypatch) -> None:
    """Patching settings attr to True makes production_admission_flag_enabled() return True."""
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)
    monkeypatch.setattr(settings, "sec_xbrl_production_admission_evaluator_enabled", True)
    assert production_admission_flag_enabled() is True


def test_settings_attr_false_no_env_returns_false(monkeypatch) -> None:
    """Patching settings attr to False with no env var returns False."""
    monkeypatch.setattr(settings, "sec_xbrl_production_admission_evaluator_enabled", False)
    monkeypatch.delenv("SEC_XBRL_PRODUCTION_ADMISSION_EVALUATOR_ENABLED", raising=False)
    assert production_admission_flag_enabled() is False
