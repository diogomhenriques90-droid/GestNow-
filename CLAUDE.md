# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```powershell
# Install dependencies
pip install -r requirements.txt

# Run locally (port 8080)
streamlit run app.py --server.port=8080
```

There are no automated tests — the CI pipeline only validates that key packages import correctly. Manual testing in the browser is the only verification method.

## Deploying

**Push to `main` triggers an automatic Cloud Build deploy.** The pipeline (`cloudbuild.yaml`) builds the Docker image, pushes it to Artifact Registry, and deploys to Cloud Run — no manual step needed.

- **Production URL:** `https://gestnow-v3-773461449136.europe-west1.run.app`
- **Cloud Run service:** `gestnow-v3`, region `europe-west1`, 2Gi memory, 2 vCPU
- **GCS bucket:** `gestnow-dados` (env var `GCS_BUCKET=gestnow-dados`)

To deploy manually (e.g., to force a redeploy without a code change):

```powershell
gcloud builds submit --config cloudbuild.yaml
```

## Git Workflow

- `dev` is the working branch. Merge to `main` when ready to ship.
- Git is available via GitHub Desktop's bundled binary:
  ```powershell
  $git = "C:\Users\Utilizador\AppData\Local\GitHubDesktop\app-3.5.8\resources\app\git\cmd\git.exe"
  & $git <command>
  ```

## Architecture

**GESTNOW v3** is a Streamlit application for managing industrial instrumentation projects (timesheets, HR, billing, fleet, quality, etc.). There is no backend server — Streamlit runs as the full stack.

All source files are flat in the repository root: `app.py`, `core.py`, `mod_admin.py`, and all `mod_*.py` files. There are no subdirectories for Python code.

### Data Layer (`core.py`)

All persistent data lives in Google Cloud Storage as CSV files under `gs://gestnow-dados/data/*.csv` — 19 CSVs loaded by `load_all()` plus additional module-specific CSVs loaded on demand. There is no database.

Key functions:
- `_cached_load_db(fn, cols_tuple, silent, _v)` — `@st.cache_data(ttl=300)` cached reader. Do **not** call directly.
- `load_db(fn, cols, silent)` — public wrapper; reads `st.session_state._fv[fn]` as a version key to support selective invalidation.
- `save_db(df, fn)` — writes CSV to GCS. For `registos.csv`, `usuarios.csv`, `folhas_ponto.csv`, it blocks if the new DataFrame loses >10% of rows and auto-creates a daily backup.
- `inv(ficheiro=None)` — cache invalidation. **Always call with the filename** (`inv("obras_lista.csv")`) after every `save_db`. Only call bare `inv()` (nuclear, clears all cache) for global reset operations (backup restore, IT admin, full-app refresh).
- `load_all()` — loads the 19 core CSVs at once; called once per render cycle in `app.py` and the result tuple is passed positionally to every module. Additional CSVs (financial, admin sub-modules) are loaded on demand inside each module via `load_db`.
- `_load_users_cached()` — separate `@st.cache_data(ttl=60)` cache for `usuarios.csv`. Use `inv("usuarios.csv")` to invalidate (this also calls `_load_users_cached.clear()`).

### Routing (`app.py`)

After login, `app.py` calls `load_all()` and routes by `st.session_state.tipo` and `st.session_state.menu_selected`:

| Tipo | Module rendered |
|---|---|
| `Admin` | `mod_admin` → sub-tabs → `mod_admin_*.py` + `mod_fat_*.py` |
| `Secretariado` | `mod_secretariado` |
| `Armazém` | `mod_armazem` |
| `Cliente` | `mod_cliente` |
| `Chefe de Equipa` / `Gestor` | `mod_chefe` or `mod_tecnico` |
| Others (Técnico) | `mod_tecnico`, `mod_inicio` |

New users are intercepted before routing for a 4-step onboarding flow (PDFs → price confirmation → profile → IBAN upload), implemented entirely in `app.py`.

### Module Structure

- **`mod_admin.py`** — Admin hub with 10 tabs. Each tab lazy-imports from a specialist module.
- **`mod_admin_*.py`** — Admin sub-modules (rh, obras, compras, frota, comercial, planeamento, qualidade, deslocacoes, dormidas, diarias, formacoes, orcamentacao, acessos_obras, faturacao, it).
- **`mod_fat_*.py`** — Financial modules (clientes, fornecedores, frota, fundos, imobilizado, obras, rh, reporting, tesouraria, fiscal, auditoria, crise, dashboard).
- **`mod_tecnico.py` / `mod_chefe.py`** — Field worker views (timesheets, sign-in, GPS check-in, requests).
- **`mod_instrumentacao.py`** — Instrument index per obra, with per-obra CSV files (`inst_{obra_key}_index.csv`).
- **`core.py`** — All shared utilities: GCS I/O, caching, `inv()`, `load_all()`, session management, auth, notifications, PDF generation, CSS injection, offline banner, audit log.
- **`translations.py`** — UI strings in PT/EN/ES/FR. Use `t("key")` for translated strings.

### Session State Conventions

- `st.session_state.user` — logged-in username
- `st.session_state.tipo` — user role (`Admin`, `Técnico`, `Chefe de Equipa`, `Secretariado`, `Armazém`, `Cliente`, `Gestor`)
- `st.session_state.cargo` — job title (used for instrumentation access)
- `st.session_state.menu_selected` — active nav item (string matching ICONS keys)
- `st.session_state._fv` — dict of `{filename: version_int}` for selective cache invalidation

### Critical Invariants

1. **After every `save_db(df, "ficheiro.csv")`, call `inv("ficheiro.csv")`** — without this the next render reads stale cached data.
2. **Never call `inv()` bare** in module files unless the operation touches every CSV simultaneously (e.g., full backup restore). Use the filename form.
3. **`load_all()` is called once in `app.py`** and the 19-tuple is passed positionally into every `render_*` function. Adding a new CSV to `load_all()` requires updating every downstream function signature.
4. **`save_db` blocks on >10% row loss** for the three critical files. If a legitimate bulk-delete is needed, bypass the check by writing directly to `_gcs_write`.
5. Backups for critical files are created automatically (daily) in `gs://gestnow-dados/data/backups/YYYY-MM-DD/`. Restore via `restore_backup(path)` in `core.py`.
