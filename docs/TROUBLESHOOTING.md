# Troubleshooting

Solutions to common issues when using the Game Theory Workbench.

---

## Installation Issues

### pygambit Build Failures

**Error**: `cargo build` or Rust compilation errors when installing pygambit

**Cause**: pygambit requires Rust toolchain for building C++ bindings.

**Solution**:
1. Install Rust from https://rustup.rs/
2. Restart your terminal
3. Retry installation:
   ```bash
   .venv/Scripts/pip install -e ".[dev]"
   ```

If still failing:
- On Windows: Install Visual Studio Build Tools with C++ support
- On macOS: Run `xcode-select --install`
- On Linux: Install `build-essential` and `libffi-dev`

---

### Virtual Environment Activation (Windows)

**Error**: `cannot be loaded because running scripts is disabled on this system`

**Cause**: PowerShell execution policy blocks script execution.

**Solution**:
```powershell
# Option 1: Change execution policy for current user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Option 2: Use cmd.exe instead
cmd /k ".venv\Scripts\activate.bat"
```

---

### Node.js Version Issues

**Error**: Frontend build fails with syntax errors or missing features

**Cause**: Node.js version too old.

**Solution**:
1. Check version: `node --version` (should be 18+)
2. Update Node.js from https://nodejs.org/
3. Clear npm cache and reinstall:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

---

## Plugin Problems

### "Plugin unavailable" Error

**Error**: API returns 400 with message about unavailable plugin

**Cause**: Plugin service not running or failed to start.

**Solution**:
1. Set up plugin virtual environments:
   ```powershell
   # Windows
   scripts/setup-plugins.ps1

   # Unix
   scripts/setup-plugins.sh
   ```

2. Restart the backend:
   ```bash
   .venv/Scripts/python -m uvicorn app.main:app --reload
   ```

3. Check startup logs for plugin errors

---

### Plugin Health Check Failures

**Error**: Backend logs show "Remote plugin failed to start: gambit"

**Cause**: Plugin subprocess crashed or can't bind to port.

**Solutions**:

1. **Check plugin venv exists**:
   ```bash
   # Replace "gambit" with the plugin name (gambit, pycid, vegas, egttools, openspiel)
   ls plugins/gambit/.venv/Scripts/python  # Windows
   ls plugins/gambit/.venv/bin/python      # Unix
   ```

2. **Test plugin manually**:
   ```bash
   cd plugins/gambit
   .venv/Scripts/python -m gambit_plugin --port=9999
   # For other plugins: pycid_plugin, vegas_plugin, egttools_plugin, openspiel_plugin
   ```

3. **Check for port conflicts**:
   ```bash
   # Windows
   netstat -ano | findstr :9999

   # Unix
   lsof -i :9999
   ```

4. **Reinstall plugin dependencies**:
   ```bash
   cd plugins/gambit
   .venv/Scripts/pip install -e ".[dev]"
   ```

---

### Port Conflicts

**Error**: Plugin fails with "Address already in use"

**Cause**: Previous plugin process didn't shut down cleanly.

**Solution**:
1. Find and kill zombie processes:
   ```powershell
   # Windows
   Get-Process python | Where-Object {$_.Path -like "*gambit*"} | Stop-Process

   # Unix
   pkill -f "gambit_plugin"
   ```

2. Restart the backend

---

## Analysis Errors

### "Conversion failed" Error

**Error**: `Conversion from [format] to [format] failed`

**Cause**: Game structure incompatible with target format.

**Common cases**:
- 3+ player games can't convert to normal form efficiently
- Imperfect information games may lose structure in conversion
- MAIDs with cycles can't become trees

**Solution**: Use the game in its native format, or simplify the game structure.

---

### Analysis Timeout

**Error**: Task status shows "failed" with timeout message

**Cause**: Game too complex for the analysis to complete in time.

**Solutions**:
1. Use a simpler/faster solver:
   ```bash
   # Try "quick" solver instead of "exhaustive"
   curl -X POST "http://localhost:8000/api/tasks?game_id=...&plugin=Nash%20Equilibrium&solver=quick"
   ```

2. Limit results:
   ```bash
   curl -X POST "...&max_equilibria=5"
   ```

3. Simplify the game (fewer players, strategies, or nodes)

---

### "Incompatible plugin" Error

**Error**: `Plugin [name] cannot run on game format [format]`

**Cause**: Analysis doesn't support the game type, even after attempting automatic format conversion.

**Example**: Running a MAID-specific analysis on an extensive-form game that can't be converted.

**Solution**:
1. Use a plugin that supports your game's format
2. Or manually convert the game first via `GET /api/games/{id}/as/{format}`

**Note**: The backend automatically attempts format conversion when possible. This error means no compatible format could be found.

---

## Frontend Issues

### Blank Canvas

**Error**: Game loads but canvas is empty

**Causes & Solutions**:

1. **WebGL not supported**:
   - Check browser console for WebGL errors
   - Update graphics drivers
   - Try a different browser

2. **Game data invalid**:
   - Check browser console for errors
   - Verify game loaded correctly: check Network tab for `/api/games/{id}` response

3. **Layout calculation failed**:
   - Game may have circular references
   - Check for orphan nodes

---

### API Connection Errors

**Error**: Frontend shows "Failed to fetch" or network errors

**Solutions**:

1. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Check CORS settings**: The backend allows all origins by default. If you modified this, ensure your frontend origin is allowed.

3. **Check port configuration**: Frontend dev server expects backend on port 8000. Verify Vite proxy config in `frontend/vite.config.ts`.

---

### Slow Rendering

**Error**: Canvas is laggy or unresponsive

**Causes**:
- Very large game (hundreds of nodes)
- Many overlays active simultaneously
- Low-end GPU

**Solutions**:
1. Reduce game size if possible
2. Disable some analysis overlays
3. Use a browser with better WebGL performance

---

## Debugging Tips

### Enable Debug Logging

**Backend**:
```python
# In app/main.py or via environment
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend**:
- Open browser DevTools (F12)
- Check Console tab for errors
- Check Network tab for API requests

### Check Plugin Subprocess Output

When running in development mode, plugin output appears in the main terminal. For more detail:

```bash
# Run plugin directly with verbose output
cd plugins/gambit
.venv/Scripts/python -m gambit_plugin --port=9999
```

### Inspect Task State

```bash
# List all tasks
curl http://localhost:8000/api/tasks

# Get specific task details
curl http://localhost:8000/api/tasks/{task_id}
```

### Test Game Parsing

```bash
# Test that a game file parses correctly
curl -X POST http://localhost:8000/api/games/upload \
  -F "file=@your-game.json" \
  -v
```

---

## Still Stuck?

1. **Check existing issues**: https://github.com/YOUR_REPO/issues
2. **Search error message**: Often reveals known solutions
3. **Create a minimal reproduction**: Smallest game/config that shows the problem
4. **Open an issue** with:
   - Error message (full text)
   - Steps to reproduce
   - Python/Node versions
   - Operating system
