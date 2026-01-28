# Technical Debt Assessment: Game Theory Workbench

## Executive Summary

The codebase is well-structured overall but has accumulated technical debt across three main areas:
1. **Code duplication** across backend, frontend, and plugins
2. **Inconsistent patterns** for error handling, logging, and state management
3. **Missing abstractions** particularly in the plugin architecture

---

## Critical Issues

### 1. Blocking the Event Loop (Async/Sync Mismatch)
**File:** `app/routes/games.py`
- The `upload_game` endpoint is `async def` but calls synchronous `parse_game(...)` directly
- CPU-bound parsing blocks the main event loop
- **Impact:** Server freezes during large file uploads; health checks fail
- **Recommendation:** Remove `async` (let FastAPI use thread pool) OR use `await run_in_threadpool(parse_game, ...)`

### 2. Race Condition in Port Allocation (TOCTOU)
**File:** `app/core/plugin_manager.py`
- `_find_free_port()` binds socket, finds port, then closes it before returning
- **Impact:** Another process can grab the port before plugin starts, causing mysterious failures
- **Recommendation:** Pass port `0` to subprocess, have it report chosen port via stdout

---

## High Priority Issues

### 3. Strategy/Payoff Logic Duplication (Plugin Architecture)
**Files:** `app/core/strategies.py`, `plugins/gambit/gambit_plugin/strategies.py`
- 100+ lines of nearly identical code duplicated for "plugin isolation"
- Bug fixes must be manually replicated between locations
- **Recommendation:** Create a shared JSON-schema based strategy module or generate plugin code from core

### 4. Bare Exception Handling Anti-Pattern (Backend)
**Files:** `app/core/plugin_manager.py`, `app/core/remote_plugin.py`
- Generic `except Exception: pass` swallows errors silently
- Masks unexpected failures, makes debugging difficult
- **Recommendation:** Replace with specific exceptions (`httpx.ConnectError`, `subprocess.TimeoutError`)

### 5. Large Component Needs Splitting (Frontend)
**File:** `frontend/src/components/panels/AnalysisPanel.tsx` (543 lines)
- Contains 4 nested sub-components that should be extracted
- Hard to test, difficult to reuse sections
- **Recommendation:** Extract `AnalysisSection`, `EquilibriumCard`, `IESDSSection` to separate files

### 6. Missing Error Boundaries (Frontend)
**Files:** Multiple components
- Malformed analysis results could crash entire panel
- No graceful degradation for invalid states
- **Recommendation:** Add React error boundaries around major sections

### 7. Hard Dependency on Global Singletons
**Files:** `app/core/registry.py`, `app/core/store.py`, `app/routes/*.py`
- Routes import global instances directly (`from app.core.store import game_store`)
- **Impact:** Unit tests can't run in parallel, mocking requires complex patching
- **Recommendation:** Use FastAPI's Dependency Injection (`Depends(get_game_store)`)

### 8. Fragile Path Resolution & Side-Effect Imports
**File:** `app/main.py`
- `Path(__file__).resolve().parent.parent` assumes specific directory nesting
- Import-time side effects populate registries (breaks if imports reordered)
- **Recommendation:** Use `get_project_root()` with sentinel file lookup; explicit `registry.scan()` instead of import-time registration

---

## Medium Priority Issues

### 9. Error Handling Inconsistency (Backend)
**Files:** `routes/games.py`, `routes/tasks.py`, `routes/analyses.py`
- Different error detail formats across routes
- No consistent error response schema
- **Recommendation:** Create `app/core/errors.py` with standardized error utilities

### 10. Code Duplication: toFraction() (Frontend)
**Files:** `AnalysisPanel.tsx`, `MatrixEquilibriumOverlay.ts`
- Identical 15-line function in two places
- **Recommendation:** Extract to `canvas/utils/fractionUtils.ts`

### 11. Overlay clear() Duplication (Frontend)
**Files:** 4 overlay classes
- Identical 6-line clear logic repeated
- **Recommendation:** Add shared method to `BaseOverlayManager`

### 12. Duplicate Bootstrap Code (Backend)
**Files:** `main.py`, `bootstrap.py`
- `_load_example_games()` defined twice with minor differences
- **Recommendation:** Keep single implementation in `bootstrap.py`

### 13. Hardcoded Magic Values (Backend)
**Files:** `plugin_manager.py`, `remote_plugin.py`, `tasks.py`, `efg_nfg.py`
- Timeouts (10.0, 5.0, 2.0), limits (10000, 100), ports scattered
- **Recommendation:** Create `app/config.py` with named constants

### 14. Task Management Inconsistency (Plugins)
- Local uses `TaskStatus.COMPLETED`, remote uses `DONE`
- Different threading models (ThreadPoolExecutor vs manual Thread)
- **Recommendation:** Unify task status enum names, document threading model

### 15. Thread Safety in GameStore (Backend)
**File:** `app/core/store.py`
- No locks on `_conversions` dict, potential race conditions
- **Recommendation:** Add `threading.Lock()` to cache operations

### 16. HTTP Error Handling Fragmentation (Plugins)
**Files:** `remote_plugin.py`, `formats/remote.py`, `conversions/remote.py`
- Three different error handling strategies for same failures
- **Recommendation:** Create shared `RemoteServiceClient` with centralized error handling

---

## Low Priority Issues

### 17. Logging Format Inconsistency (Backend)
- Mixed f-strings and %-formatting for logs
- **Recommendation:** Standardize on one style

### 18. Type Hints Inconsistency (Backend)
- Mixed `callable` vs `Callable`, some missing return types
- **Recommendation:** Audit and standardize type hints

### 19. Console Logging in Production (Frontend)
**Files:** `analysisStore.ts`, `gameStore.ts`, `useSceneGraph.ts`
- Debug `console.log()` calls appear in production
- **Recommendation:** Implement logging abstraction with levels

### 20. Non-Serializable State (Frontend)
**File:** `uiStore.ts`
- Uses `Map<string, ViewMode>` which isn't JSON-serializable
- **Recommendation:** Use plain object or persist to localStorage

<!-- IGNORE
### 21. Missing Accessibility (Frontend)
- Clickable divs instead of buttons
- Missing ARIA labels and keyboard navigation
- **Recommendation:** Convert to semantic HTML, add ARIA attributes -->

### 22. Unvalidated Type Casting (Frontend)
**Files:** Multiple overlays and panels
- `as NashEquilibrium[]` without runtime validation
- **Recommendation:** Use type guards instead of force casting

### 23. Plugin Restart Logic Bug (Backend)
**File:** `plugin_manager.py`
- Restart counter increment inconsistent between methods
- **Recommendation:** Audit and fix counter increment location

### 24. Missing Input Validation (Frontend)
**File:** `GameSelector.tsx`
- No file size or MIME type validation on upload
- **Recommendation:** Add validation before upload

---

## Architectural Recommendations

### Plugin Interface Abstraction
- No formal interface for remote plugin HTTP contract
- Capabilities discovery requires running plugins
- **Recommendation:** Define `PluginHTTPContract` spec, add static capability registry

### Configuration Centralization
- Plugin config scattered: `plugins.toml`, `__main__.py` ANALYSES dict, inline closures
- **Recommendation:** Single source of truth for plugin capabilities

### Shared Remote Plugin Helpers
- `create_remote_parser()` and `create_remote_conversion()` closures duplicate HTTP logic
- **Recommendation:** Extract to `RemoteServiceClient` class

---

## Recommended Refactoring Order

**Critical Fixes (do first):**
1. Fix async/sync mismatch in `upload_game` endpoint
2. Fix TOCTOU race in port allocation

**Quick Wins (1-2 hours each):**
1. Extract `_load_example_games()` to single location
2. Create `app/config.py` for magic constants
3. Extract `toFraction()` to shared utility
4. Replace bare `except Exception:` with specific types

**Medium Effort (2-4 hours each):**
1. Convert global singletons to FastAPI DI
2. Create error response utilities for backend routes
3. Add thread locks to GameStore
4. Split AnalysisPanel into smaller components
5. Add error boundaries to frontend

**Larger Refactoring (4+ hours):**
1. Unify task management between local/remote plugins
2. Create RemoteServiceClient abstraction
3. Address strategy/payoff duplication across plugins
4. Implement explicit plugin registration (remove import-time side effects)

---

## Completed Refactoring (Checkpoints 1-8)

- [x] Fix async/sync mismatch in `upload_game` endpoint (#1)
- [x] Fix TOCTOU race in port allocation with retry logic (#2)
- [x] Bare exception handling → specific exceptions (#4)
- [x] Split AnalysisPanel into smaller components (#5)
- [x] Add React error boundaries (#6)
- [x] Create `app/config.py` for magic constants (#13)
- [x] Extract `toFraction()` to shared utility (#10)
- [x] Overlay clear() duplication → `overlayUtils.ts` (#11)
- [x] Duplicate bootstrap code consolidated (#12)
- [x] Thread safety in GameStore (#15)
- [x] Create error response utilities (#9)
- [x] Standardize logging format (%-formatting) (#17)
- [x] Frontend logging abstraction with logger.ts (#19)
- [x] Non-serializable state in uiStore (#20)
- [x] Plugin restart logic bug (#23)
- [x] File upload validation (#24)
- [x] Create `app/core/paths.py` for robust path resolution (#8 partial)
- [x] Create `app/core/http_client.py` with RemoteServiceClient (#16) - Plan A
- [x] Task status normalization (queued→pending, done→completed) (#14) - Plan C
- [x] Convert global singletons to FastAPI DI (#7) - Plan B (fully removed globals)

---

## Detailed Implementation Plans for Large Refactoring

### Plan A: RemoteServiceClient Abstraction (#16)

**Goal:** Unify HTTP client code across `remote_plugin.py`, `formats/remote.py`, `conversions/remote.py`

**Current State:**
- 3 different POST implementations with similar error extraction
- Duplicated backoff/polling logic
- Inconsistent error handling (some raise ValueError, some return AnalysisResult)

**Implementation:**

1. **Create `app/core/http_client.py`:**
   ```python
   class RemoteServiceClient:
       def __init__(self, base_url: str, service_name: str):
           self.base_url = base_url
           self.service_name = service_name

       def post(self, endpoint: str, json: dict, timeout: float) -> dict:
           """POST with standardized error handling."""

       def get(self, endpoint: str, timeout: float) -> dict:
           """GET with standardized error handling."""

       def poll_until_complete(
           self,
           task_id: str,
           cancel_event: Optional[Event] = None,
       ) -> dict:
           """Poll task status with exponential backoff."""

       @staticmethod
       def extract_error_message(response: httpx.Response) -> str:
           """Extract error from various response formats."""
   ```

2. **Update consumers:**
   - `remote_plugin.py`: Use `client.post()` and `client.poll_until_complete()`
   - `formats/remote.py`: Use `client.post()` for parsing
   - `conversions/remote.py`: Use `client.post()` for conversion

3. **Consolidate timeout config:**
   - Move all HTTP timeouts to a single `HTTPClientConfig` class in `app/config.py`
   - Keep separate logical groups (parse, convert, analyze) but in one place

**Files to modify:**
- Create: `app/core/http_client.py`
- Modify: `app/core/remote_plugin.py`, `app/formats/remote.py`, `app/conversions/remote.py`
- Modify: `app/config.py` (consolidate timeout configs)

**Risk:** Low - straightforward extraction, existing tests cover functionality

---

### Plan B: Global Singletons → FastAPI Dependency Injection (#7)

**Goal:** Replace direct imports of global instances with FastAPI's `Depends()` pattern

**Current State:**
- 5 global singletons: `game_store`, `registry`, `task_manager`, `conversion_registry`, `plugin_manager`
- Routes import these directly: `from app.core.store import game_store`
- Tests require complex patching to mock

**Implementation:**

1. **Create `app/dependencies.py`:**
   ```python
   from functools import lru_cache

   @lru_cache
   def get_game_store() -> GameStore:
       return GameStore()

   @lru_cache
   def get_registry() -> Registry:
       return Registry()

   @lru_cache
   def get_task_manager() -> TaskManager:
       return TaskManager()

   # ... etc
   ```

2. **Update route signatures:**
   ```python
   # Before
   from app.core.store import game_store

   @router.get("/games")
   def list_games():
       return game_store.list_summaries()

   # After
   from app.dependencies import get_game_store

   @router.get("/games")
   def list_games(store: GameStore = Depends(get_game_store)):
       return store.list_summaries()
   ```

3. **Update tests to override dependencies:**
   ```python
   def test_list_games():
       mock_store = Mock(spec=GameStore)
       app.dependency_overrides[get_game_store] = lambda: mock_store
       # ... test
       app.dependency_overrides.clear()
   ```

4. **Remove global instances from modules** (keep factory functions only)

**Migration order:**
1. `game_store` (most used, highest test value)
2. `task_manager` (used in task routes)
3. `registry` (used in analysis routes)
4. `conversion_registry` (used in games routes)
5. `plugin_manager` (startup only, lowest priority)

**Files to modify:**
- Create: `app/dependencies.py`
- Modify: All route files (`games.py`, `tasks.py`, `analyses.py`)
- Modify: `app/core/store.py`, `app/core/tasks.py`, `app/core/registry.py` (remove global instances)
- Modify: Tests to use dependency overrides

**Risk:** Medium - affects many files, requires careful testing

---

### Plan C: Task Status Unification (#14)

**Goal:** Align task status enums between backend and plugins

**Current State:**
| Backend | Plugins |
|---------|---------|
| `PENDING` | `QUEUED` |
| `COMPLETED` | `DONE` |

**Options:**

**Option 1: Adapt at boundary (Recommended)**
- Keep internal enums as-is
- Add mapping in `remote_plugin.py` when reading plugin responses:
  ```python
  STATUS_MAP = {"queued": "pending", "done": "completed"}
  def normalize_status(plugin_status: str) -> str:
      return STATUS_MAP.get(plugin_status, plugin_status)
  ```
- Pro: No plugin changes, backward compatible
- Con: Translation layer adds complexity

**Option 2: Update plugins to match backend**
- Change plugins to use `PENDING`/`COMPLETED`
- Pro: Consistent naming
- Con: Breaking change if external tools use plugin API

**Option 3: Create shared status package**
- Create `shared/task_status.py` that both import
- Pro: Single source of truth
- Con: Adds deployment complexity (shared package)

**Recommended: Option 1** - least invasive, maintains plugin independence

**Implementation:**
1. Add status normalization to `RemoteServiceClient.poll_until_complete()`
2. Document the mapping in `plugins/README.md`
3. Add tests for status translation

**Files to modify:**
- Modify: `app/core/http_client.py` (if created) or `app/core/remote_plugin.py`
- Create: `plugins/README.md` or update existing docs

**Risk:** Low - isolated change with clear boundary

---

### Plan D: Strategy/Payoff Logic Duplication (#3)

**Goal:** Eliminate 100+ lines of duplicated strategy enumeration code

**Current State:**
- `app/core/strategies.py`: Works with Pydantic models (274 lines)
- `plugins/gambit/gambit_plugin/strategies.py`: Works with plain dicts (100 lines)
- Same algorithms, different data access patterns

**Options:**

**Option 1: JSON-schema based shared module (Recommended)**
- Create `shared/strategies.py` that works on plain dicts
- Core can wrap it to accept Pydantic models
- Plugin imports directly

**Option 2: Generate plugin code from core**
- Write a code generator that transforms model-based code to dict-based
- Pro: Always in sync
- Con: Complex tooling, hard to debug generated code

**Option 3: Plugin imports core (rejected)**
- Would create circular dependency
- Violates plugin isolation principle

**Implementation (Option 1):**

1. **Create `shared/strategies.py`:**
   ```python
   """Strategy utilities that operate on plain dicts (JSON-like).

   Used by both app/core (via wrapper) and plugins directly.
   """

   def enumerate_strategies_dict(game: dict) -> dict[str, list[dict]]:
       """Enumerate all pure strategies for each player."""
       # Implementation using dict access: game["root"], node["actions"], etc.

   def resolve_payoffs_dict(game: dict, profile: dict) -> dict[str, float]:
       """Resolve payoffs for a strategy profile."""
   ```

2. **Update `app/core/strategies.py`:**
   ```python
   from shared.strategies import enumerate_strategies_dict, resolve_payoffs_dict

   def enumerate_strategies(game: ExtensiveFormGame) -> dict[str, list[Strategy]]:
       """Wrapper that converts model to dict, calls shared, converts back."""
       result_dict = enumerate_strategies_dict(game.model_dump())
       return {player: [Strategy(**s) for s in strats] for player, strats in result_dict.items()}
   ```

3. **Update plugin to import from shared:**
   ```python
   # plugins/gambit/gambit_plugin/strategies.py
   from shared.strategies import enumerate_strategies_dict, resolve_payoffs_dict

   # Re-export for backward compatibility
   enumerate_strategies = enumerate_strategies_dict
   resolve_payoffs = resolve_payoffs_dict
   ```

4. **Package structure:**
   ```
   thrones/
   ├── shared/              # New shared package
   │   ├── __init__.py
   │   └── strategies.py
   ├── app/
   │   └── core/
   │       └── strategies.py  # Wrapper with Pydantic support
   └── plugins/
       └── gambit/
           └── gambit_plugin/
               └── strategies.py  # Imports from shared
   ```

5. **Update plugin setup:**
   - Add `shared` to plugin's Python path or install as editable package
   - Update `plugins/gambit/pyproject.toml` to depend on shared

**Files to modify:**
- Create: `shared/__init__.py`, `shared/strategies.py`
- Modify: `app/core/strategies.py` (add wrapper)
- Modify: `plugins/gambit/gambit_plugin/strategies.py` (import from shared)
- Modify: `plugins/gambit/pyproject.toml` (add shared dependency)

**Risk:** Medium - requires plugin packaging changes, test both paths

---

## Recommended Implementation Order

1. **Plan A: RemoteServiceClient** (~2-3 hours)
   - Standalone improvement
   - Reduces code, improves consistency
   - Foundation for Plan C

2. **Plan C: Task Status Unification** (~1 hour)
   - Simple mapping in RemoteServiceClient
   - Low risk

3. **Plan B: Dependency Injection** (~4-6 hours)
   - Enables parallel testing
   - Large but straightforward mechanical change

4. **Plan D: Strategy Duplication** (~4-6 hours)
   - Most complex due to packaging changes
   - Do last to avoid disrupting other work

---

## Test Coverage Gaps to Address

- Remote plugin network failure scenarios
- Plugin restart mid-analysis recovery
- Cancellation during network issues
- Task cleanup in remote plugins
- Format/conversion registration with missing plugins
- Parallel test isolation (currently blocked by global singletons)
