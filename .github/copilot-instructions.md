# Copilot / AI agent instructions (repository-level)

This repository is currently empty (no source files, manifests, or CI configs were found at the time this note was generated).

Use these instructions when an AI coding agent is asked to work in this repo. Keep changes small and ask clarifying questions when the project type is unknown.

1) First-pass discovery (what to look for — exact filenames)
  - `package.json`, `package-lock.json`, `pnpm-lock.yaml` -> Node/TypeScript/JS projects
  - `pyproject.toml`, `requirements.txt`, `setup.py` -> Python projects
  - `go.mod` -> Go projects
  - `Cargo.toml` -> Rust projects
  - `pom.xml`, `build.gradle` -> Java/Kotlin
  - `Makefile`, `Dockerfile` -> build/run helpers
  - `.github/workflows/*.yml` -> CI expectations
  - `README.md` -> high-level project goals and quickstart

2) If you find a package manifest, extract exact commands to run from it
  - Node: prefer `npm ci` then `npm test` or `npm run test`; inspect `scripts` in `package.json` and give examples (e.g., `npm run build`).
  - Python: prefer `python -m venv .venv` or using the user's preferred venv, then `pip install -r requirements.txt` or `pip install .` and `pytest` if present.
  - Go: run `go test ./...` and look for `Makefile` for additional targets.

3) Drafting instructions and PRs
  - Keep PRs small and focused (single feature or bug). If no tests exist, add minimal unit tests alongside code changes.
  - When changing behavior, include a short reproducible example (input, expected output) in the test or README.
  - If you add CI config, keep it minimal and non-destructive (run unit tests only).

4) Patterns and conventions to surface in this repo (none discovered yet)
  - If a `src/` or `lib/` folder is present, prefer edits there over adding top-level modules.
  - If TypeScript is detected (tsconfig.json), prefer adding or updating types instead of using `any`.

5) Integration points to note (how to discover them)
  - Search for environment variables in `.env`, `config/`, or `src/config` to discover external services.
  - Look for `docker-compose.yml` or `Dockerfile` for local integration with databases or caches.
  - Check `.github/workflows` for external service credentials usage or deployments.

6) When adding to this file
  - Replace the discovery checklist above with concrete commands and examples found in the repo (sample `npm` commands, `pytest` invocation, Docker commands, etc.).
  - Add 2–3 short examples from real files (e.g., "To run the app: `npm run start` — see `package.json` scripts").

7) Questions for the repo owner (include these in the PR body if unknown)
  - What language/runtime should be prioritized? (Node/Python/Go/etc.)
  - Preferred test command and CI gate (unit tests only, lint + tests, or full integration tests?)
  - Any repository-specific linting/formatting rules (prettier, eslint, black, isort, golangci-lint)?

If you want, I can re-run discovery after you add the project files (package manifest, README, or sample source). Once files exist I will update this document with concrete commands, key files, and 2–3 inline examples from the codebase.

---
Generated: no files found in repository root when this file was created. Update this doc after adding project files.
