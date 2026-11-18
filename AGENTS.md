# WeAgent instructions

## Sources of truth

- For changes that affect domain behavior or ownership, start with `CONTEXT-MAP.md`.
- For changes to Education terminology, ownership, authorization, durability, adoption/projection, or cross-context behavior, also read `docs/education-specs/CONTEXT.md`. Treat its boundaries as current; if intentionally changing them, update the context documentation and affected contract tests with the implementation.
- Use `README.md` for setup and package entry points and `docs/tech/README.md` for the current technical-document index. Verify architecture claims against the current code, tests, and package manifests; older design and AI-collaboration documents may describe earlier layouts.

## Validation

When a package is affected, run validation from that package directory. Prefer targeted tests first, then broaden validation in proportion to the change.

- Backend (`backend/`): run targeted pytest paths with `python -m pytest <test-path> -q`; the full suite is `python -m pytest tests -q`. Do not invoke `pytest backend/tests` from the repository root.
- Web (`frontend/`): run each affected standalone contract test with `node tests/<name>.test.js`, then run `npm run build` when the web application or build output is affected.
- Desktop (`clients/desktop/`): `npm run build`.
- Android (`clients/android/`): use `npm run build` for ordinary application changes. For Capacitor configuration, plugin, or native-integration changes, use `npm run cap:sync`, which already builds the application.
- After runtime or image-affecting changes under `backend/app/sandbox/container/` or to `backend/app/sandbox/Dockerfile`, rebuild `weagent-sandbox:latest` using the command in `README.md`; if Docker is unavailable, report that the rebuild was not run.
