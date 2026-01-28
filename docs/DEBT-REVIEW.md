**1. Blocking the Event Loop (Async/Sync Mismatch)**

* **File:** `app/routes/games.py`
* **The Issue:** The `upload_game` endpoint is defined as `async def`, but it calls `parse_game(...)` directly. Since `parse_game` is CPU-bound (parsing large JSON/EFG files) and synchronous, this **blocks the main event loop**.
* **Impact:** During a large file upload/parse, the entire server freezes. Health checks fail, and other users cannot interact with the API.
* **Recommendation:** Either remove `async` (letting FastAPI run it in a thread pool) or use `await run_in_threadpool(parse_game, ...)` to offload the CPU work.

**2. Race Condition in Port Allocation (TOCTOU)**

* **File:** `app/core/plugin_manager.py`
* **The Issue:** `_find_free_port()` binds a socket to find a port, then *closes it* before returning the number.
* **Impact:** There is a window between closing the socket and the subprocess starting where another process can grab that port, causing the plugin launch to fail mysteriously.
* **Recommendation:** Pass port `0` to the subprocess (letting it bind dynamically) and have the subprocess report its chosen port back via stdout parsing.

### Architecture & Testability Gaps (Add to Architectural Concerns)

**3. Hard Dependency on Global Singletons**

* **Files:** `app/core/registry.py`, `app/core/store.py`, `app/routes/*.py`
* **The Issue:** Routes import global instances directly (`from app.core.store import game_store`).
* **Impact:** This makes unit testing extremely brittle. Tests cannot run in parallel because they share the same memory state, and you cannot easily mock the store for specific scenarios without complex `unittest.mock` patching.
* **Recommendation:** Use FastAPI's Dependency Injection system (`Depends(get_game_store)`) to inject these singletons. This allows tests to override them with clean/mocked instances effortlessly.

**4. Fragile Path Resolution & Side-Effect Imports**

* **Files:** `app/main.py`
* **The Issue:**
* **Paths:** `Path(__file__).resolve().parent.parent` assumes a specific directory nesting. This breaks if the app is refactored, containerized differently, or packaged (e.g., PyInstaller).
* **Imports:** `from app.plugins import discover_plugins` relies on side-effects at import time to populate registries. Reordering imports by an auto-formatter could break the app.


* **Recommendation:**
* Use a robust `get_project_root()` utility that looks for a sentinel file (like `pyproject.toml`).
* Switch to explicit plugin registration (e.g., `registry.scan()`) rather than import-time side effects.
