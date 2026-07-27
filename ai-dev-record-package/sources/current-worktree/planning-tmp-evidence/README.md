# 当前工作区验证证据说明

本目录来自当前工作区 `.planning/tmp` 中筛选出的有效证据。这里不保存浏览器 profile、cache 或临时运行目录，只保留能辅助说明 AI 协作开发结果的截图、日志和 UAT JSON。

这些文件不是独立文档，必须结合顶层说明文档、`.planning/phases/*/VERIFY.md`、UAT 指南和分支提交记录一起阅读。

## 桌面端 Toolset 验证截图

- `desktop-tools-header-after.png`：桌面 Toolset 页面头部与导航调整后的早期验证截图，用于说明桌面端已出现工具集入口和页面结构。
- `desktop-tools-header-after-2.png`：头部区域细节复查截图，用于辅助确认布局修正不是一次性偶然结果。
- `desktop-tools-header-after-screen.png`：桌面窗口整体画面截图，用于证明页面在真实窗口中能正常展示。
- `desktop-tools-window-after.png`：桌面端窗口级视图截图，用于证明 Toolset 页面与 Electron 外壳集成后可用。
- `desktop-tools-header-confirm.png`：后续确认截图，用于证明桌面端 Toolset 入口和头部布局在最终检查中仍存在。
- `desktop-tools-exact-window.png`：精确窗口尺寸下的桌面端验证截图，用于观察固定窗口尺寸下是否出现明显遮挡或布局异常。

## 桌面端宽窄视口修复截图

- `desktop-tools-cdp-wide.png`：通过浏览器调试或 CDP 方式记录的宽视口桌面端 Toolset 状态。
- `desktop-tools-cdp-narrow.png`：窄视口状态截图，用于对比响应式布局。
- `desktop-tools-fixed-wide.png`：宽视口布局修复后的截图。
- `desktop-tools-fixed-narrow.png`：窄视口布局修复后的截图。
- `desktop-tools-fixed-wide-v2.png`：第二轮宽视口修复确认截图。
- `desktop-tools-fixed-narrow-v2.png`：第二轮窄视口修复确认截图。

这些截图共同说明桌面端 Toolset 页面不是只在单一尺寸下可用，而是经过了宽窄窗口复查和修正。

## Web Toolset 验证截图

- `web-tools-sidebar-wrench.png`：Web 端侧边栏工具入口截图，用于证明 Web Toolset 入口存在。
- `web-tools-wrench-v2.png`：Web 端工具入口或图标修复后的确认截图，用于说明入口视觉和导航经过复查。

## Toolset 缺陷修复截图

- `toolset-icon-debug-before.png`：工具集图标修复前的截图，用于记录问题状态。
- `toolset-icon-debug-after.png`：工具集图标修复后的截图，用于证明问题已被修正。
- `toolset-detail-sidebar-debug.png`：工具详情侧栏问题排查截图，用于记录 UAT/调试时发现的侧栏体验问题。
- `toolset-detail-sidebar-fixed.png`：工具详情侧栏修复后的截图。
- `toolset-count-fixed.png`：工具数量或 tab count 修复后的截图，用于关联 `UAT-017` 一类计数一致性问题。

这一组截图的价值在于展示 AI 协作开发中的“发现问题、记录问题、修复问题、复查问题”的过程。

## 日志证据

- `dev-backend.log`：后端开发服务早期运行日志，用于保留调试环境和服务运行证据。
- `dev-backend-current.log`：后端开发服务当前或后续运行日志，用于辅助排查接口、沙箱和 runtime 行为。
- `dev-frontend.log`：前端开发服务早期运行日志，用于保留 Web build/dev server 运行证据。
- `dev-frontend-current.log`：前端开发服务当前或后续运行日志，用于辅助确认页面调试和前端服务状态。

日志不作为主要阅读材料，主要用于在需要复核时辅助证明当时服务曾运行、报错或输出过相关状态。

## UAT JSON

- `uat-desktop-multi-agent-mcp.json`：桌面端多 Agent / MCP 相关 UAT 记录。它是比截图更结构化的验收证据，可与 Phase 04 的 provider runtime、MCP binding、capability projection 验证记录一起阅读。

## 阅读建议

优先阅读顶层文档和 `.planning` 下的 VERIFY/REPORT 文件，再回到本目录查看截图和日志。截图负责证明“界面和状态确实出现过”，日志和 JSON 负责辅助证明“运行链路和 UAT 过程确实被记录过”。
