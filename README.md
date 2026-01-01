# Game Theory Workbench MVP

This repository contains a minimal, canvas-first MVP that mirrors the design goals documented in `design/`. It ships with:

- A FastAPI backend that exposes a default trust game and runs continuous analyses through a plugin registry
- A Gambit-backed Nash Equilibrium plugin (via `pygambit`) that computes mixed equilibria for the default game
- A static frontend that renders a simple canvas, status bar, and LLM input stub based on the wireframes

## Running locally

1. Use Python 3.12 and ensure you have `pip` for that interpreter (create a venv if needed to provision it automatically; otherwise run `python3.12 -m ensurepip --upgrade`). Install dependencies; building `pygambit` can take a couple of minutes while the C++ core is compiled:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

2. Start the FastAPI app with the static frontend:

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

3. Open the prototype UI at http://localhost:8000 to explore the trust-game canvas and live analysis summaries.

## Extending

- Add new analyses under `app/plugins/`; they are auto-discovered on startup and register themselves with the registry in `app/core/registry.py`.
- Replace the default trust game in `app/main.py` with real data or loaders from Gambit files.
- Expand the frontend canvas (`frontend/index.html`) to visualize probabilities as branch thickness and outcomes as markers, matching the design language.

## Windows setup and dependencies

- **Create a Python 3.12 virtual environment (Windows)**: this repository targets Python 3.12. From PowerShell or cmd, create and activate a `.venv` before installing dependencies:

   PowerShell:

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

   cmd.exe:

   ```cmd
   py -3.12 -m venv .venv
   .\.venv\Scripts\activate.bat
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

- **Rust / Cargo dependency**: building some native extensions (used by parts of the toolchain) requires Rust's package manager `cargo`. Install Rust (and `cargo`) from https://rustup.rs/ and ensure `cargo` is on your `PATH` before installing Python dependencies.

