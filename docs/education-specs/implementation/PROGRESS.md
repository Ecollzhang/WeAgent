# Education MVP 进度

## 2026-07-27

- 创建 Goal，范围限定为 Education MVP。
- 验证根目录 `.env` 被 `.gitignore` 忽略。
- 将设计文档迁移到 `docs/education-specs`，修复 9 个失效的本地链接。
- 将逐阶段人工审核改为自动验证连续推进，保留产品教师审批门。
- 提交：`e40a025 docs(education): relocate specs and streamline review gates`。
- 启动 backend、frontend、runtime/RAG 三条只读代码勘察。
- 建立后端和前端构建基线，记录现有阻塞。
- 完成三条架构勘察，确认 edu 服务、前端占位、RAG 授权和工具闭环的真实缺口。
- 以红绿测试修复核心灰度迁移的 SQLite 兼容问题，并保留管理员关闭的灰度配置。
- 灰度修复后后端全量回归从 `68 errors` 收敛为 `14 failed, 241 passed`。
