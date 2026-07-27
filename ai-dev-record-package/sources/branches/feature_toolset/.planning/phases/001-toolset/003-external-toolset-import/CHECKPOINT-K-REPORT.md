# CHECKPOINT-K: Capability Delete/Unbind, Toolset Icons, and Count Consistency

## Scope

This checkpoint closes UAT-014, UAT-015, and the follow-up count consistency bug UAT-017.

Out of scope:
- Built-in Tool runtime implementation.
- Curated Tool recommendation design.
- MCP runtime expansion beyond existing import/display behavior.

## Changes

### UAT-014: Delete and Unbind

- Added `GET /api/capabilities/<capability_id>/delete-impact`.
- Added `DELETE /api/capabilities/<capability_id>`.
- Added `DELETE /api/agents/<agent_id>/capabilities/<binding_id>`.
- User-created capabilities are archived by setting `source = archived` and moving the slug to an archived namespace.
- Archived capabilities are hidden from normal capability listing.
- Deleting a user capability removes default Agent bindings for the current user.
- Capability versions, security audits, and call records are preserved.
- Built-in capabilities cannot be deleted.
- Plugin install records are marked `removed` when a plugin capability is archived.
- The Agent edit form now uses the real unbind API for persisted capability bindings.
- Toolset category tab counts now exclude archived capabilities, matching the capability card list.

### UAT-015: Icon Rendering

- Toolset cards and detail headers now use a shared icon resolver.
- Icon priority is:
  1. capability manifest/tool icon
  2. category icon
  3. type icon
  4. fallback icon
- Added an Element UI icon allowlist and alias mapping.
- Mapped unavailable `el-icon-console` to a valid fallback.
- Added explicit icon font size and line height for capability cards and detail headers.
- Fixed a later `.detail-header span` selector that overrode the right detail sidebar icon container. The selector now targets only subtitle text via `.detail-heading > div > span`.

### UAT-017: Count Consistency After Delete

- Root cause: `/api/capabilities` hid archived capabilities, but `/api/toolsets/categories` still counted them in category/type badges.
- Fixed `_counts_by_category` to exclude `Capability.source == archived`.
- Added a regression test that archives one Skill and verifies the category `skill` count drops accordingly.
- Verified the real page with Chrome headless: after archiving two of four Skills, the `Skill` tab displayed `Skill 2` and only two Skill cards were visible.
- Note: the left category total can still be larger than the active tab count because it sums all visible capability types in that category, for example `2 Skill + 2 Tool = 4`.

## Verification

Commands run:

```powershell
python -m pytest tests\test_capability_api.py -q
node tests\toolset-ui-contract.test.js
node tests\agent-capability-selector-contract.test.js
python -m pytest tests\test_toolset_categories.py tests\test_capability_api.py tests\test_capability_import_confirm.py tests\test_capability_projection.py -q
python -m pytest tests\test_toolset_categories.py::test_category_counts_exclude_archived_capabilities -q
python -m pytest tests\test_toolset_categories.py tests\test_capability_api.py -q
npm run build
```

Results:
- Capability API focused suite: 12 passed.
- Toolset UI contract: passed.
- Agent capability selector contract: passed.
- Backend regression subset: 27 passed.
- Category count regression: 1 passed.
- Toolset category + capability API regression subset: 18 passed.
- Frontend production build: passed with existing asset-size warnings.
- Chrome headless screenshot verification for the right detail sidebar showed `.detail-icon` computed as `display:flex` and icon center offset `0,0`.
- Chrome headless count verification showed `Skill 2` with two visible Skill cards after two of four Skills were archived.

## Remaining UAT

- Open `/tools` and verify a user-created/imported Skill/MCP/Plugin/Tool shows a delete button in the right detail panel.
- Delete a user-created capability and confirm it disappears from the toolset page.
- Confirm the active type tab count decreases after deleting a user-created capability.
- Edit an existing Agent, remove a persisted capability binding, and confirm it disappears after refresh.
- Verify built-in Tool/MCP cards do not show a delete button.
- Verify Git/terminal/database Tool icons render as clear full-size icons.
- Continue UAT-016 separately: real built-in Tool runtime implementation and curated built-in Tool design.
