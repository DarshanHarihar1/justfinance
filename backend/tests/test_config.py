"""Regression tests for ``app.core.config``.

These don't touch the filesystem or DB — they validate that env var parsing
behaves as expected, especially the cases the design hinges on.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture()
def fresh_settings(monkeypatch: pytest.MonkeyPatch):
    """Reset the lru_cache and reload the config module under controlled env."""

    def _factory(**env: str):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        # Block .env discovery by pointing at a non-existent file.
        monkeypatch.chdir("/")
        from app.core import config

        importlib.reload(config)
        return config.get_settings()

    return _factory


def test_cors_origins_parsed_from_comma_separated_string(fresh_settings) -> None:
    s = fresh_settings(CORS_ORIGINS="http://a.example, http://b.example , http://c.example")
    assert s.cors_origins == ["http://a.example", "http://b.example", "http://c.example"]


def test_cors_origins_falls_back_to_default(fresh_settings) -> None:
    s = fresh_settings()
    assert s.cors_origins == ["http://localhost:5173"]


def test_database_is_pooled_is_a_bool(fresh_settings) -> None:
    s_true = fresh_settings(DATABASE_IS_POOLED="true")
    s_false = fresh_settings(DATABASE_IS_POOLED="false")
    assert s_true.database_is_pooled is True
    assert s_false.database_is_pooled is False


def test_session_max_age_default_is_30_days(fresh_settings) -> None:
    s = fresh_settings()
    assert s.session_max_age == 60 * 60 * 24 * 30
