"""Tests for the plugin manager (subprocess supervisor)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from app.core.plugin_manager import (
    PluginConfig,
    PluginManager,
    PluginProcess,
    _find_free_port,
    load_plugins_toml,
)


class TestFindFreePort:
    def test_returns_port_number(self):
        port = _find_free_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_different_ports(self):
        ports = {_find_free_port() for _ in range(5)}
        # Should get at least 2 different ports in 5 attempts
        assert len(ports) >= 2


class TestPluginConfig:
    def test_defaults(self):
        config = PluginConfig(name="test", command=["python", "-m", "test"])
        assert config.auto_start is True
        assert config.restart == "on-failure"
        assert config.cwd == "."


class TestLoadPluginsToml:
    def test_load_nonexistent_file(self, tmp_path):
        settings, plugins = load_plugins_toml(tmp_path / "nonexistent.toml")
        assert settings == {}
        assert plugins == []

    def test_load_valid_toml(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [settings]
            startup_timeout_seconds = 5
            max_restarts = 2

            [[plugins]]
            name = "test-plugin"
            command = ["python", "-m", "test_plugin"]
            cwd = "plugins/test"
            auto_start = true
            restart = "on-failure"
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        settings, plugins = load_plugins_toml(toml_file)
        assert settings["startup_timeout_seconds"] == 5
        assert settings["max_restarts"] == 2
        assert len(plugins) == 1
        assert plugins[0].name == "test-plugin"
        assert plugins[0].command == ["python", "-m", "test_plugin"]
        assert plugins[0].cwd == "plugins/test"
        assert plugins[0].auto_start is True

    def test_load_multiple_plugins(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [[plugins]]
            name = "plugin-a"
            command = ["python", "-m", "a"]

            [[plugins]]
            name = "plugin-b"
            command = ["python", "-m", "b"]
            auto_start = false
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        _, plugins = load_plugins_toml(toml_file)
        assert len(plugins) == 2
        assert plugins[0].name == "plugin-a"
        assert plugins[1].name == "plugin-b"
        assert plugins[1].auto_start is False


class TestPluginManager:
    def test_load_config(self, tmp_path):
        toml_content = textwrap.dedent("""\
            [settings]
            startup_timeout_seconds = 3

            [[plugins]]
            name = "test"
            command = ["python", "-m", "test"]
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
            command = ["python", "-m", "my_plugin"]
        """)
        toml_file = tmp_path / "plugins.toml"
        toml_file.write_text(toml_content, encoding="utf-8")

        manager = PluginManager(config_path=toml_file)
        manager.load_config()

        assert manager.get_plugin("my-plugin") is not None
        assert manager.get_plugin("nonexistent") is None

    def test_stop_all_no_processes(self):
        """stop_all should handle case where no processes are running."""
        manager = PluginManager()
        manager.stop_all()  # Should not raise


class TestPluginProcess:
    def test_default_state(self):
        config = PluginConfig(name="test", command=["python"])
        pp = PluginProcess(config=config)
        assert pp.port == 0
        assert pp.process is None
        assert pp.url == ""
        assert pp.healthy is False
        assert pp.restart_count == 0
        assert pp.analyses == []
