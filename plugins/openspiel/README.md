# OpenSpiel Plugin

CFR (Counterfactual Regret Minimization) and exploitability analysis for extensive-form games.

## Platform Support

OpenSpiel only works on **Linux and macOS**. On Windows, you must use WSL (Windows Subsystem for Linux).

## Windows Setup (WSL)

1. Install WSL if not already installed:
   ```powershell
   wsl --install
   ```

2. Open a WSL terminal and navigate to the project:
   ```bash
   cd /mnt/c/path/to/thrones
   ```

3. Create the plugin venv in WSL:
   ```bash
   python3 -m venv plugins/openspiel/.venv
   plugins/openspiel/.venv/bin/pip install -e plugins/openspiel[dev]
   ```

4. Update `plugins.toml` to use WSL:
   ```toml
   [[plugins]]
   name = "openspiel"
   command = ["wsl", "plugins/openspiel/.venv/bin/python", "-m", "openspiel_plugin"]
   cwd = "plugins/openspiel"
   auto_start = true
   restart = "on-failure"
   ```

## Linux/macOS Setup

```bash
python3 -m venv plugins/openspiel/.venv
plugins/openspiel/.venv/bin/pip install -e plugins/openspiel[dev]
```

## Analyses

- **CFR Equilibrium**: Compute approximate Nash equilibrium using CFR, CFR+, or MCCFR
- **Exploitability**: Measure distance from Nash equilibrium (nash_conv)
- **CFR Convergence**: Track exploitability over CFR iterations
- **Best Response**: Compute optimal counter-strategy to a policy

## Running Tests

```bash
plugins/openspiel/.venv/bin/python -m pytest plugins/openspiel/tests/ -v
```
