"""Tests for the plugin manager (Docker container discovery)."""
from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.plugin_manager import (
    PluginConfig,
    PluginManager,
    PluginProcess,
    load_plugins_toml,
)


class TestPluginConfig:
    def test_defaults(self):
        config = PluginConfig(name="test")
        assert config.url == ""

    def test_with_url(self):
        config = PluginConfig(name="test", url="http://localhost:5000")
        assert config.url == "http://localhost:5000"


class TestLoadPluginsToml:
    def test_load_nonexistent_file(self, tmp_path):
        settings, plugins = load_plugins_toml(tmp_path / "nonexistent.toml")
        assert settings == {}
        assert plugins == []

    def test_load_valid_toml(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [settings]
            startup_timeout_seconds = 5

            [[plugins]]
            name = "test-plugin"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        settings, plugins = load_plugins_toml(toml_file)
        assert settings["startup_timeout_seconds"] == 5
        assert len(plugins) == 1
        assert plugins[0].name == "test-plugin"

    def test_load_multiple_plugins(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [[plugins]]
            name = "plugin-a"

            [[plugins]]
            name = "plugin-b"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        _, plugins = load_plugins_toml(toml_file)
        assert len(plugins) == 2
        assert plugins[0].name == "plugin-a"
        assert plugins[1].name == "plugin-b"

    def test_url_from_environment(self, tmp_path, monkeypatch):
        """Plugin URLs should come from environment variables."""
        toml_content = textwrap.dedent("""\
            [[plugins]]
            name = "gambit"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        # Set environment variable
        monkeypatch.setenv("GAMBIT_URL", "http://custom-host:9999")

        # Reload the module to pick up the new env var
        import importlib
        import app.config
        importlib.reload(app.config)
        import app.core.plugin_manager
        importlib.reload(app.core.plugin_manager)
        from app.core.plugin_manager import load_plugins_toml as reload_load

        _, plugins = reload_load(toml_file)
        assert plugins[0].url == "http://custom-host:9999"


class TestPluginManager:
    def test_load_config(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [settings]
            startup_timeout_seconds = 3

            [[plugins]]
            name = "test"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        manager = PluginManager(config_path=toml_file)
        manager.load_config()
        assert "test" in manager.plugins
        assert manager._startup_timeout == 3

    def test_load_config_missing_file(self, tmp_path):
        manager = PluginManager(config_path=tmp_path / "missing.toml")
        manager.load_config()
        assert len(manager.plugins) == 0

    def test_healthy_plugins_empty(self):
        manager = PluginManager()
        assert manager.healthy_plugins() == []

    def test_get_plugin(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [[plugins]]
            name = "my-plugin"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        manager = PluginManager(config_path=toml_file)
        manager.load_config()

        assert manager.get_plugin("my-plugin") is not None
        assert manager.get_plugin("nonexistent") is None

    def test_stop_all_noop(self):
        """stop_all should be a no-op (Docker manages containers)."""
        manager = PluginManager()
        manager.stop_all()  # Should not raise

    def test_loading_status_initial(self):
        manager = PluginManager()
        status = manager.loading_status
        assert status["loading"] is False
        assert status["total_plugins"] == 0
        assert status["plugins_ready"] == 0


class TestPluginProcess:
    def test_default_state(self):
        config = PluginConfig(name="test")
        pp = PluginProcess(config=config)
        assert pp.url == ""
        assert pp.healthy is False
        assert pp.analyses == []
        assert pp.info == {}

    def test_with_url(self):
        config = PluginConfig(name="test", url="http://localhost:5000")
        pp = PluginProcess(config=config, url="http://localhost:5000")
        assert pp.url == "http://localhost:5000"
