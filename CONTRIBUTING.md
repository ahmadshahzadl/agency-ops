# Contributing to AgencyOps

Thank you for your interest in contributing! AgencyOps is open-source and welcomes contributions of all kinds — bug fixes, new features, documentation improvements, and more.

## Getting started

1. **Fork** the repository and clone your fork.
2. Set up the project locally by following the [Quick start](README.md#quick-start) guide.
3. Create a new branch for your work:
   ```bash
   git checkout -b feat/your-feature-name
   ```

## Development workflow

### Backend (FastAPI + Python)

- Code lives in `backend/app/`
- Run tests before submitting: `cd backend && pytest`
- Follow existing patterns for new endpoints (router → service → model)
- New database changes require an Alembic migration:
  ```bash
  alembic revision --autogenerate -m "describe your change"
  alembic upgrade head
  ```

### Frontend (React + TypeScript)

- Code lives in `frontend/src/`
- Run the dev server: `cd frontend && npm run dev`
- Follow existing component and API client patterns

## Submitting a pull request

1. Make sure your branch is up to date with `main`.
2. Run the backend test suite (`pytest`) and confirm no regressions.
3. Write a clear PR title and description explaining what you changed and why.
4. Link any related issues in the PR description.

## Reporting bugs

Open a [GitHub Issue](../../issues) with:

- A clear title and description
- Steps to reproduce
- Expected vs actual behaviour
- Your OS, Python version, and Node version

## Suggesting features

Open a [GitHub Issue](../../issues) with the `enhancement` label. Describe the use case and why it would benefit agency teams.

## Code style

- **Python**: PEP 8, type hints encouraged
- **TypeScript**: strict mode, no `any` unless unavoidable
- Keep PRs focused — one feature or fix per PR

## License

By contributing, you agree that your contributions will be licensed under the [GPL-3.0 License](LICENSE).
