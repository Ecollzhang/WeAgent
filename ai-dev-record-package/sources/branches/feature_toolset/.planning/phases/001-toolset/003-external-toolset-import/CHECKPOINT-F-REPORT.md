# Checkpoint F Report: Runtime Projection 和 Asset Draft Sync

## 目标

让已经保存到 DB 的 Skill bundle 在 session runtime 中完整写出，并允许 Agent 修改 `SKILL.md` 或附属资产后生成待确认草稿；草稿发布前必须重新审计，高风险需要专家 override。

## 已完成

- `capability_projection_service` 已把 `CapabilityVersionAsset` 加入 Skill projection：
  - 每个 asset 带 `path`、`kind`、`content`、`sha256`、`mime_type`、`runtime_path`。
  - Agent 的 skill index 仍只展示该 Agent 已授权的 Skill 视图。
- container runtime projection 已写出完整 Skill bundle：
  - `.weagent/skills/<runtime_id>/SKILL.md`
  - `.weagent/skills/<runtime_id>/scripts/...`
  - `.weagent/skills/<runtime_id>/references/...`
  - `.weagent/skills/<runtime_id>/manifest.json`
  - `.weagent/drafts/skills/<runtime_id>/baseline.json`
- baseline 现在覆盖所有受控文件：
  - `SKILL.md`
  - 已投影的 asset 文件
  - 每个文件的路径、kind、checksum、content snapshot、长度和 mime type
- draft collector 已支持文件级 diff：
  - 只改 `SKILL.md` 的旧流程保持兼容。
  - 修改 asset 时生成 `diff.changed`、`diff.files`、`diff.proposed_assets`。
  - 重复收集同一个 checksum 不会重复产生草稿。
- draft publish 已支持 asset 新版本：
  - 发布时创建新的 `CapabilityVersion` 和对应 assets。
  - 未提供 `proposed_assets` 时会保留源版本 assets，避免纯 Markdown 草稿丢失附属文件。
  - fork draft 也会保留/应用 draft assets。
- draft publish 已接入重新审计：
  - 发布前审计 `SKILL.md` 和 proposed assets。
  - 高风险缺少 `override_confirmed` 时阻断。
  - override 成功后写入 `CapabilitySecurityAudit`，并关联新版本。

## RED 测试

先新增并运行以下测试，确认实现前失败：

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_capability_asset_drafts.py
```

失败点符合预期：

- projection 没有 `assets`。
- container 没写出 `scripts/check.mjs`。
- draft collector 没检测 asset diff。
- `publish_draft` 没创建 asset 新版本。
- 高风险 asset draft 没要求专家 override。

## GREEN 验证

实现后通过：

```powershell
python -m pytest tests\test_capability_projection.py tests\test_capability_container_projection.py tests\test_capability_asset_drafts.py
```

结果：

- `9 passed`

回归验证：

```powershell
python -m pytest tests\test_capability_skill_draft_sync.py tests\test_capability_api.py
```

结果：

- `11 passed`

## 注意事项

- 当前 draft 表仍复用 `diff` JSON 保存 `proposed_assets`，没有新增 draft asset 表；这符合 v1 “先形成真实闭环”的范围。
- `CapabilitySecurityAudit` 会在 draft publish 时先记录，再补上新 `capability_version_id`。
- 测试输出仍包含项目既有 SQLAlchemy legacy/deprecation warnings，未在本 checkpoint 中处理。
