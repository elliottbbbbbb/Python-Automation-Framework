## **Codebase Analysis — OSRS-Automation-Framework**

This document summarizes a concise, actionable analysis of the repository at the time of inspection (Jan 03, 2026). It maps architecture, highlights risks and tech-debt, and lists prioritized remediation recommendations.

**Overview:**
- **Project:** OSRS automation toolkit (Python)
- **Top-level layout:** `src/osrsbot` package with subpackages: `core`, `commands`, `services`, `models`, `queries`, `scripts`, `app`, `utils`, plus `images` and `fonts` resources.
- **Entry points:** CLI/UI entry: [src/osrsbot/main.py](src/osrsbot/main.py) -> `osrsbot.app.menu:main`. Runner: [src/osrsbot/core/runner.py](src/osrsbot/core/runner.py).

**Architecture mapping (concise):**
- **`core/`**: Orchestration and bot primitives. Key files: [src/osrsbot/core/base_bot.py](src/osrsbot/core/base_bot.py) (abstract Bot, run loop), [src/osrsbot/core/runner.py](src/osrsbot/core/runner.py) (`ScriptRunner` initializes services and runs scripts), `game_interface.py` (window/attach abstractions).
- **`services/`**: Low-level platform and perception services. Examples: `mouse_service.py`, `interception_mouse_service.py`, `screen_service.py`, `template_match_service.py`, `template_ocr_service.py`, `status_socket_service.py`, `walker_service.py`. These encapsulate OS/window I/O and image processing.
- **`commands/`**: Higher-level game actions and domain operations (`game_actions.py`, `bank_actions.py`, `inventory_actions.py`) that use services to perform in-game behaviors.
- **`queries/`**: Image/visual checks and template queries (e.g., `bank_queries.py`, `game_queries.py`, `inventory_queries.py`) — used by commands and state.
- **`models/`**: Configuration and data models; `config.py` centralizes config loading/saving and default values; includes `mnist_cnn.onnx` model used by OCR.
- **`scripts/`**: Example and production scripts (bots) that implement specific behaviors; they invoke `ScriptRunner` or subclass `Bot`.
- **`app/`**: Local UI and calibration tooling (menu, debug UI, calibration flows).
- **`utils/`**: Pure helpers (color, coordinate, template helpers, timing helpers).

**Key behaviors & flow:**
- `ScriptRunner` loads `Config`, instantiates `GameInterface`, `MouseService`/`InterceptionMouseService`, `ScreenService`, template/ocr services, `StatusSocketService` and optional `WalkerService`, plus `GameState` and `GameActions`. Scripts are run via `runner.run_script(...)` which supports Bot classes, bot instances, or callables.
- `Config` reads/writes `config.json` and exposes `get()` helpers; sensible defaults are created when missing.

**Dependencies (from pyproject.toml):**
- Notable runtime deps: `pyautogui`, `PyWinCtl`, `mouse`, `keyboard`, `pytesseract`, `Pillow`, `opencv-python`, `numpy`, `onnxruntime`, `interception-python`, `pyclick`, `pyserial`, `pywin32`, `python-dotenv`.
- Dev: `pytest`, `pytest-cov`, `black`, `ruff`.

**Tests & quality:**
- Tests exist under `tests/` and include unit and integration tests. Test harness expects local capabilities (image files, optional interception/hardware). `pyproject.toml` configures Black, isort style expectations.

**Findings — code, risks, and tech-debt (observed):**
- Small number of `TODO` markers in code (inventory detection, docs) — low tech debt surface.
- Config file creation writes defaults to disk automatically. This is convenient but can overwrite or create files in unexpected locations if `config_file` path isn't validated.
- Many OS / device-specific dependencies (kernel-level interception, window attach) — operational complexity and platform fragility.
- Use of the environment and filesystem: `Config`, `StatusSocketService` and tests use direct `open()` calls; ensure proper exception handling and path resolution.
- No obvious hardcoded API keys or credentials found in `src/`. Many string constants for in-game coordinates and colors exist in `config.py` defaults.
- No high-risk use of `eval()`/`pickle.loads()` in `src/` discovered during scan. Some uses appear in vendored site-packages in the virtual environment (normal).

**Security notes:**
- Avoid committing `env/` or virtualenv dependencies; ensure no secrets are stored in `config.json` under version control.
- If project ever integrates networked features, validate and harden `status_socket_service.py` and any file/JSON endpoints before exposing to untrusted networks.

**Code quality / maintainability observations:**
- Clear separation of concerns (services vs commands vs core) — good for testability and extension.
- `Config` is a heavy central object; consider immutability or validation layers to avoid accidental runtime mutation.
- Some user-facing prints include non-ASCII characters that render oddly in certain terminals (observed in `base_bot.py`); minor cosmetic issue.

**Prioritized recommendations (short-term → long-term):**
1. **Add CI static checks**: run `ruff`/`flake8` and `black` on push to detect style and obvious issues. (High impact, low effort)
2. **Run full test suite in CI** (mock or limit hardware-dependent tests) and mark hardware tests as `integration`/`manual`. (High impact)
3. **Harden `Config` file handling**: validate `config_file` path, avoid silent overwrite, and document sample `config.json`. Consider `Config.save()` returning error details. (Medium)
4. **Secrets policy**: Add `.gitignore` for local `config.json` or provide `config.example.json`, and recommend using `python-dotenv` or OS credential stores for sensitive values. (High)
5. **Service initialization resilience**: Add clearer error/error codes when optional components (Interception, Status Socket) fail; surface user guidance strings. (Medium)
6. **Document architecture**: Add a short `docs/ARCHITECTURE_SUMMARY.md` (2–3 pages) describing the runtime initialization sequence (what `ScriptRunner` creates). (Low effort)

**Suggested immediate next steps (pick one):**
- Generate CI configuration (GitHub Actions) to run `ruff`, `black --check`, and `pytest -q` (with environment matrix). I can scaffold this.
- Run local static analysis and tests now and attach the results.

**Files created/edited during this analysis:**
- Analysis file: [docs/CODEBASE_ANALYSIS.md](docs/CODEBASE_ANALYSIS.md)

If you want, I can now scaffold a minimal GitHub Actions workflow to run linters and tests, or run local static analysis next — which would you prefer?
