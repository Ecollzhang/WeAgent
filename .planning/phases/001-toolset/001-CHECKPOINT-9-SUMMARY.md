# Checkpoint 9 Summary: End-to-End Regression

**Date:** 2026-05-29
**Branch:** `feature/toolset`
**Commit scope:** Regression contract tests and phase completion evidence.

## Completed

- Added backend regression contract tests for preservation risks introduced by toolset draft sync:
  - multi-agent `send_chain` result shape remains unchanged when no Skill drafts are present;
  - delegated Agent result shape remains unchanged;
  - tool result payloads remain attached to Agent responses;
  - message serialization preserves artifact summary data;
  - message serialization preserves progress elements.
- Added frontend regression contract tests for existing display surfaces:
  - sandbox multi-agent chain mode remains present;
  - chain send path remains present;
  - realtime `agent_progress` event handling remains present;
  - file/artifact event handling remains present;
  - tool result display data remains carried on Agent messages;
  - `MessageBubble` still exposes current progress and artifact elements;
  - artifact preview event/component remains available.
- Re-ran complete backend capability plus regression suite.
- Re-ran frontend capability UI contract and production build.

## Verification

Backend focused regression:

```powershell
python -m pytest tests/test_toolset_regression_contract.py -q
```

Result:

- `2 passed`

Frontend contract tests:

```powershell
node tests\capability-ui-contract.test.js
node tests\toolset-regression-contract.test.js
```

Result:

- `capability UI contract ok`
- `toolset regression contract ok`

Backend capability plus regression:

```powershell
python -m pytest tests/test_capability_models.py tests/test_capability_service.py tests/test_capability_api.py tests/test_capability_projection.py tests/test_capability_container_projection.py tests/test_capability_sandbox_integration.py tests/test_capability_tool_audit.py tests/test_capability_mcp_runtime.py tests/test_capability_skill_draft_sync.py tests/test_toolset_regression_contract.py -q
```

Result:

- `35 passed`
- Warnings are existing SQLAlchemy/deprecation warnings plus current `datetime.utcnow` deprecation warnings.

Frontend build:

```powershell
npm run build
```

Result:

- Build completed.
- Existing bundle-size warnings remain for `img/bg...png`, `chunk-vendors`, and app entrypoint size.

## Evidence Map

- Multi-agent message display preservation: frontend chain mode/chain send contract plus backend `send_chain` result-shape regression.
- Agent realtime progress display preservation: frontend `agent_progress` and `MessageBubble.currentProgress` contract plus backend progress element serialization.
- Artifact display preservation: frontend `file_write`, `artifactElements`, and `ArtifactPreview` contract plus backend artifact summary serialization.
- Toolset happy path: capability API, UI contract, projection, built-in Tool audit, MCP runtime, Plugin no-execution, and Skill draft sync regression suite.

## Boundary

This checkpoint provides automated contract and integration evidence. It does not replace a final human/browser UAT pass against a running Docker-backed sandbox session.

## Next

Phase 001 is ready for review. A practical next step is manual UI acceptance against a running stack or preparing a PR/merge review for `feature/toolset`.
