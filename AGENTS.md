# Repository Guidelines

## Project Structure & Module Organization
The root contains deployment guides and Docker assets used for Cloud Build and Cloud Run. `frontend/` is a Vite + React app; its key entry points are `src/main.jsx` and `src/App.jsx`, with UI pieces under `src/components/` and shared assets in `src/assets/`. `server/` hosts the FastAPI service with `server/main.py` as the default Vertex AI-backed entry point (additional variants target NanoBanana and Google APIs). Ad-hoc smoke tests (`test_server.py`, `test_genai.py`) sit at the repository root for quick environment validation.

## Build, Test, and Development Commands
- `npm install` / `npm run dev` inside `frontend/`: install dependencies and start the hot-reload UI on port 5173.
- `npm run build` produces the optimized bundle, and `npm run lint` enforces the ESLint rules defined in `eslint.config.js`.
- `pip install -r requirements.txt` prepares the FastAPI backend; run it locally with `uvicorn server.main:app --reload --port 8080`.
- `python test_server.py` checks Python package availability; `python test_genai.py` verifies Google GenAI credentials and a trivial content request when the API key is exported.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation for Python modules; prefer explicit function names that mirror API endpoints (`generate_images_with_vertex_simple`, etc.). JavaScript/JSX files use modern ES modules with eslint recommended + React Hooks presets—let ESLint surface unused symbols and keep components in PascalCase while hooks remain `camelCase`. Static assets should stay in kebab-case.

## Testing Guidelines
These scripts act as smoke tests rather than full suites; run them before submitting changes to confirm dependencies resolve. When adding FastAPI routes, introduce pytest-style cases under `tests/` and wire them into `python -m pytest`. Frontend changes should pair with React Testing Library checks in `frontend/src/__tests__/` and keep `npm run test` (via Vitest) green once added.

## Commit & Pull Request Guidelines
Recent history lacks structured messages—please adopt imperative, descriptive titles (e.g., `feat: add expression prompt logger`). Reference related guides (`CLOUD_BUILD_GUIDE.md`, `SECRET_UPDATE_GUIDE.md`) when the change touches deployment or credentials. PRs should summarize user-facing effects, list validation commands, include screenshots for UI work, and link to any tracking tickets for traceability.

## Security & Configuration Tips
Never commit secrets; populate `.env` files locally and rely on Cloud Secret Manager for deployments as described in `SECRET_UPDATE_GUIDE.md`. Confirm Google Application Default Credentials or NanoBanana keys are present before running generators, and rotate them following `UPDATE_SECRET.md` whenever sharing the environment.
