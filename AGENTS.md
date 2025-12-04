# Repository Guidelines

## Project Structure & Module Organization
- Backend lives in `backend/`: FastAPI entry `main.py`, config in `config.py`, database layer in `db.py`, HTTP routes under `api/routers/`, and business logic in `utils/` (model loading, runs, image handling). Persistent data sits in `data/` (models, uploads, polygons) with schema in `schema.sql`.
- Frontend lives in `frontend/`: Next.js App Router pages in `app/`, shared UI in `components/`, hooks in `hooks/`, API client in `lib/api.ts`, and helpers in `utils/`. Static assets live in `public/`.
- Test suites: Python tests in `backend/tests/`; frontend Vitest tests in `frontend/__tests__/`.

## Build, Test, and Development Commands
- Backend dev server: `cd backend && source venv/bin/activate && uvicorn main:app --reload`.
- Backend tests: `cd backend && source venv/bin/activate && pytest` (add `--cov` for coverage).
- Backend quality: `black . && isort . && flake8 && mypy .` from `backend/` when the venv is active.
- Frontend dev server: `cd frontend && npm run dev` (build with `npm run build`, production start with `npm start`).
- Frontend tests: `cd frontend && npm test` (watch mode `npm test -- --watch`, coverage `npm run test:coverage`).
- Frontend lint: `cd frontend && npm run lint`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, prefer type hints; format with Black + isort, keep flake8 and mypy clean. Modules/functions are snake_case; classes are PascalCase.
- TypeScript/React: Follow ESLint defaults; favor functional components, hooks, and `tsx/ts` extensions. Use camelCase for vars/functions, PascalCase for components, and kebab-case for filenames in `components/` and `hooks/` folders.
- Paths: avoid hardcoding absolute paths; use `data/` subfolders for persisted artifacts and `public/` for static assets.

## Commit & Pull Request Guidelines
- Commits are short, imperative, and scoped (repo history favors concise messages like `clean` or `added tests`); keep related changes together.
- Pull requests should include: purpose/summary, linked issue or context, key screenshots for UI updates, and test evidence (`pytest`/`npm test`/coverage flags). Call out migrations, schema touches (`schema.sql`), or model file expectations (`data/models/`) explicitly.
- Keep backend and frontend changes split by commit when practical to simplify review.

## Security & Configuration Tips
- Never commit secrets; prefer `.env` files (backend uses `python-dotenv`) and keep model weights in `backend/data/models/` out of version control if large.
- Validate paths via existing helpers (`utils/security.py`) and reuse validation logic (`utils/validation.py`, `frontend/utils/validation.ts`) rather than ad-hoc checks.
- When adding new upload or file-handling code, ensure writes stay under `backend/data/` and avoid blocking calls inside request handlers.
