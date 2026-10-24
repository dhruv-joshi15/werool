# Vercel services deployment

## Import settings

- Repository: `dhruv-joshi15/werool`.
- Root Directory: `.` (the repository root).
- Application Preset / project Framework: **Services**.
- Services: **backend** → `backend/`, FastAPI; **frontend** → `frontend/`, Vite.
- Node.js: 22. Backend Python: 3.12, selected by `backend/.python-version`.
- Clear old project-wide install/build/output overrides. Services-mode build settings belong in each service, not at the top level.
- Leave `VITE_API_BASE_URL` and `DATA_DIR` unset. No binding URL environment variables are needed.

The project-wide preset must not be Other, FastAPI, Vite or a root Python app. The [Vercel Services guide](https://vercel.com/kb/guide/vercel-services) requires the Services project framework along with the `services` configuration.

## Why there are only two services

The former `api/index.py` only re-exported the FastAPI app. Along with root `requirements.txt` and `.python-version`, it advertised an unnecessary third Python application. Those deployment-only root files were removed. The real entry point remains `backend/app/main.py`, explicitly selected as `app.main:app` relative to the backend service. No API implementation was removed.

## Public routing and bindings

The root `vercel.json` is the authoritative configuration:

1. `/api` and `/api/*` route to **backend**.
2. `/docs`, `/docs/*` and `/openapi.json` route to **backend**, preserving interactive API documentation.
3. Everything else routes to **frontend**.

No destination `path`, prefix transform or FastAPI `root_path` is applied. The service receives the original `/api/v1/...` path. See [official service routing](https://vercel.com/docs/services/routing).

The frontend service's SPA fallback applies only to extensionless application paths. It excludes API paths, asset/source directories, Vite internal modules and file-extension requests. This keeps JavaScript responses intact in local service development while allowing browser route refreshes. Once `/api` selects the backend, an unknown route remains a backend JSON 404; it never falls through to the SPA.

**Bindings: none.** Both services have explicit public routes. The static React application calls the API from the browser using same-origin `/api/v1/...`; there is no server-side caller service. Runtime-only internal binding URLs are not available to a static Vite build or browser. The backend reads local snapshot files and does not call the frontend. See [official service bindings](https://vercel.com/docs/services/bindings). Docker's Nginx proxy and Vite's development proxy remain local tools, not Vercel server-side service calls.

## Snapshot packaging

The backend build command runs `python scripts/prepare_deployment.py`. Before writing anything, it checks the source manifest's SHA-256 identity and normalized snapshot checksum. It then stages only the manifest and normalized JSON into `backend/data/`; raw records are not copied. This generated directory is Git-ignored and explicitly included by the backend service's `functions` configuration.

The API resolves data relative to its module location. A checkout prefers source `data/`, avoiding stale staged copies after ingestion. An independent backend bundle uses its own `data/`. Docker retains its explicit `DATA_DIR=/data`. No network ingestion or persistent writes occur inside API handlers.

The backend's standalone pinned `requirements.txt` matches the lock file. Vercel CLI's Python dependency discovery rejected a relative `-r requirements.lock.txt` include during local services startup, so the service now exposes the complete pinned list directly.

## Verification performed

- Current official `https://openapi.vercel.sh/vercel.json` downloaded and used to validate the final configuration. Standard draft-04 validation and stricter const/property-name checks both passed.
- Vercel CLI **65.2.0**, `vercel dev --local`: detected exactly backend/FastAPI and frontend/Vite, with no root app. No account linking or cloud deployment was performed.
- All six API endpoints passed through the local Vercel router, preserving `/api/v1`. The saved snapshot ID, 744/744 matched targets and period metrics remained consistent.
- `/`, `/decision-explorer` and `/accuracy/2026-01-15` returned SPA HTML; JavaScript entry requests returned scripts instead of HTML. `/docs` and `/openapi.json` were served by the backend. Unknown and duplicated-prefix API routes returned JSON 404s.
- Full browser interaction audit passed through that router: all eight metric cards, controls, exports, target selection, both daily charts, outcome isolation, dialogs, navigation and mobile layout. No browser page errors.
- Frontend TypeScript/Vite production build passed.
- **18 backend tests passed**, including checksum staging, an isolated real-data backend bundle with no source-root access, and checkout preference over a stale staged copy. One upstream Starlette/httpx deprecation warning remains.
- Backend Docker image rebuilt successfully; Compose configuration validated; restarted backend became healthy. All six API endpoints also passed through the existing Docker dashboard on port 5174.

The first temporary current-CLI download ran out of disk space. Its download cache was removed; a smaller install succeeded and supplied the CLI used above. The older globally installed CLI 48.2.9 was not used to validate services.

A hosted production deployment and its final function bundle have not been verified. The above checks validate the configuration, actual local services router, frontend production build and isolated snapshot packaging; they do not claim a successful cloud deployment.

## Reproduce locally

From the repository root:

```sh
python3 backend/scripts/prepare_deployment.py
npx vercel@65.2.0 dev --local --listen 127.0.0.1:3011
```

In another terminal:

```sh
python3 backend/scripts/verify_service_routes.py --base-url http://127.0.0.1:3011
python3 backend/scripts/verify_api.py --base-url http://127.0.0.1:3011
cd frontend
node scripts/interactions.mjs http://127.0.0.1:3011
```

`vercel dev` starts development servers; snapshot staging is an explicit command for reproducing the independent bundle. During cloud builds it is the backend service build command. Standard local Docker/Vite startup commands are unchanged; see the README.

Before committing/pushing this configuration, confirm the two service names, the public routes above (including API docs), and that no internal-only services or bindings are required. This confirmation is a requested review step, not a Vercel platform requirement.
