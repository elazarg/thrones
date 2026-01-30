# OpenSpiel Plugin

CFR (Counterfactual Regret Minimization) and exploitability analysis for extensive-form games.

## Platform Support

OpenSpiel only works on **Linux and macOS**. The `open_spiel` Python package does not build on Windows.

### Windows Status

**This plugin is disabled on Windows by default** (`skip_on_windows = true` in plugins.toml).

While WSL can run OpenSpiel, there's a fundamental issue: Python importing modules from an NTFS mount (the Windows filesystem) causes blocking I/O in WSL2, making the plugin hang indefinitely during startup.

### Workaround for Windows Users

If you need OpenSpiel on Windows, you must clone the plugin to WSL's native filesystem:

1. Install WSL if not already installed:
   ```powershell
   wsl --install
   ```

2. Clone/copy the plugin to WSL's native filesystem (not /mnt/...):
   ```bash
   wsl
   mkdir -p ~/thrones-plugins
   cp -r /mnt/d/path/to/thrones/plugins/openspiel ~/thrones-plugins/
   cd ~/thrones-plugins/openspiel
   python3 -m venv .venv
   .venv/bin/pip install -e ".[openspiel,dev]"
   ```

3. Run the plugin manually from WSL:
   ```bash
   cd ~/thrones-plugins/openspiel
   .venv/bin/python -m openspiel_plugin --port=8100 --host=0.0.0.0
   ```

4. Configure the main app to connect to it as an external service (not auto-managed).

## Linux/macOS Setup

```bash
cd plugins/openspiel
python3 -m venv .venv
.venv/bin/pip install -e ".[openspiel,dev]"
```

The plugin will auto-start with the main application.

## Analyses

- **CFR Equilibrium**: Compute approximate Nash equilibrium using CFR, CFR+, or MCCFR
- **Exploitability**: Measure distance from Nash equilibrium (nash_conv)
- **CFR Convergence**: Track exploitability over CFR iterations
- **Best Response**: Compute optimal counter-strategy to a policy

## Running Tests

```bash
.venv/bin/python -m pytest tests/ -v
```
