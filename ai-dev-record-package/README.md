# WeAgent AI 协作开发记录交付包

本目录用于展示 WeAgent 项目中“人类成员与 AI 协作完成开发”的过程证据。它不是源码包，而是开发记录、规划文档、协作归档、阶段验证和原始参考材料的整理包。

## 阅读顺序

1. `01-项目说明文档.md`：先了解项目目标、交付内容和本包边界。
2. `02-AI协作与开发记录说明.md`：了解这些材料如何证明 AI 协作过程。
3. `03-完整解析解读文档.md`：按时间和分支阅读完整开发演进。
4. `04-SPEC-SKILL-RULE体系解读.md`：重点查看比赛关注的 Spec、Skill、Rules、Archive 体系。
5. `05-分支贡献与演进时间线.md`：查看三个分支各自贡献。
6. `06-项目文件夹总结.md`：了解项目结构和每类目录承担的角色。
7. `07-素材索引与来源清单.md`：核对原始材料来源。

## 包含范围

- 三个指定分支中的文档、`.planning` 规划记录、`docs/ai-collab` AI 协作记录、技术报告和 toolset 说明文件。
- 外层原始参考材料，包括 3 个 PDF 和 1 个 Markdown 草案。
- 当前工作区 `.planning/tmp` 中有效的验证截图、日志和 UAT JSON。

## 不包含范围

- 不打包完整源码。
- 不提取 PDF 全文。
- 不打包 `.planning/tmp` 中的浏览器 profile、cache 或运行时临时目录。
- 不打包 `.claude/settings.local.json` 或任何本地 AI 工具 settings 文件。

## 来源分支

- `origin/agent_adapter`
- `origin/feature/toolset`
- `origin/combine/toolset_v1.1.0`

完整源文件保存在 `sources/` 下，分支证据索引保存在 `sources/branch-evidence/` 下。
