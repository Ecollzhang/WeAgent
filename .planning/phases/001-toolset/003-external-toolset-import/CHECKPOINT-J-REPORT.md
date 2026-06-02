# Checkpoint J Report: MCP Manifest Frontend Entry and NPX Manifest Compatibility

## Scope

Checkpoint J responds to the real UAT question: users can see MCP capabilities, but there was no clear frontend path to add one.

This checkpoint adds:
- A dedicated MCP manifest import API.
- A frontend `MCP manifest` source in the toolset import wizard.
- Static manifest discovery for NPX and zip import outputs, so they can contain Skill / MCP / Plugin definitions instead of only `SKILL.md`.

## Implemented Changes

### Backend

- Added `POST /api/capabilities/import/mcp-manifest`.
- Added `capability_service.import_mcp_manifest(...)`.
- The MCP endpoint accepts only manifest capabilities whose `type` is `mcp`.
- Extended import preview discovery:
  - `SKILL.md` remains supported.
  - JSON files with `schema_version = weagent.capability/v1` and `capabilities[]` are now recognized.
  - Manifest candidates can be `skill`, `mcp`, or `plugin`.
- Extended confirm persistence:
  - Selected manifest candidates are converted into persisted capabilities.
  - Manifest-defined MCP entries keep command, args, tools, permissions, and source metadata.

### Frontend

- Added `importMcpManifest(...)` API wrapper.
- Added `MCP manifest` source to `Tools.vue` import wizard.
- The wizard now supports:
  - Editing MCP manifest JSON.
  - Generating a local preview.
  - Showing inferred permissions.
  - Selecting one or more MCP definitions.
  - Saving them into the active toolset category.

## Verification

Commands run:

```powershell
python -m pytest tests\test_capability_import_preview.py tests\test_capability_import_confirm.py tests\test_capability_api.py -q
node tests\toolset-ui-contract.test.js
python -m pytest tests\test_toolset_categories.py tests\test_capability_mcp_runtime.py tests\test_capability_import_preview.py tests\test_capability_import_confirm.py tests\test_capability_npx_import_sandbox.py tests\test_capability_api.py -q
npm run build
git diff --check
```

Results:
- Backend focused suite: 20 passed.
- Backend regression subset: 34 passed.
- Frontend toolset contract: passed.
- Frontend production build: passed, with existing asset-size warnings.
- `git diff --check`: no whitespace errors; only existing CRLF normalization warnings.

## Remaining UAT

- Open the toolset page and verify the import wizard shows `MCP manifest`.
- Paste or use the default Memory MCP manifest and confirm it is saved under the active category.
- Bind the imported MCP to an Agent with `run_command` granted.
- Start a sandbox session and verify MCP start/list/call/stop against the session-level runtime.

## Follow-Up Fix: NPX Skills Repo Import

During UAT, `npx skills add eze-is/web-access` failed with:

```text
Failed to clone https://github.com/eze-is/web-access.git: Error: spawn git ENOENT
```

Root cause:
- The import container used `node:22-alpine`, which does not include `git`.
- After git was available, `skills add` still prompted for agent selection unless its own `--yes --global` flags were passed.

Fix:
- NPX import sandbox now uses `node:22`, which includes git.
- Parsed `npx skills add <source>` commands are normalized to `npx --yes skills add --yes --global <source>`.

Verification:
- Real Docker command installed `eze-is/web-access` and produced `/tmp/import-home/.agents/skills/web-access/SKILL.md`.
- Real backend `preview_npx("npx skills add eze-is/web-access")` returned `web-access Skill` and scanned `.agents/skills/web-access/SKILL.md`.
- `python -m pytest tests\test_capability_npx_import_sandbox.py tests\test_capability_import_security.py -q` passed.
- 003 regression subset of 34 backend tests passed.

## Follow-Up Fix: Ignore NPM Cache in Import Preview

During UAT, NPX preview displayed paths such as:

```text
.npm-cache/_cacache/content-v2/sha512/...
```

Judgment:
- This is not reasonable product behavior.
- These files are package-manager cache artifacts created by npm/npx while downloading the installer and dependencies.
- They are not imported Skill/MCP source files and should not be shown or audited as user-visible content.

Fix:
- Directory and zip import collection now ignore package cache directories:
  `.npm-cache`, `.npm`, `_cacache`, `.pnpm-store`, `node_modules`, `.git`.
- The same cache names are included in package-cache validation as defense in depth.

Verification:
- Added `test_preview_directory_ignores_npm_cache_artifacts`.
- Real backend `preview_npx("npx skills add eze-is/web-access")` returned:
  - `FILES: 15`
  - `HAS_NPM_CACHE_FILE: False`
  - `HAS_NPM_CACHE_RISK: False`
- 003 regression subset of 44 backend tests passed.
