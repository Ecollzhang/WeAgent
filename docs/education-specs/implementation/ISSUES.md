# Education MVP 问题台账

## EDU-BASE-001：仓库根目录运行后端测试无法导入 `app`

- 发现时间：2026-07-27
- 模块：测试基线
- 等级：P2
- 现象：在仓库根目录执行 `python -m pytest backend/tests -q` 时出现
  `ModuleNotFoundError: No module named 'app'`。
- 根因：现有测试以 `backend` 为工作目录设计，仓库根目录未设置对应 Python path。
- 处理：基线和后续回归统一从 `backend` 目录运行 `python -m pytest tests -q`。
- 状态：已规避；不改变现有测试入口。

## EDU-BASE-002：SQLite 下灰度配置清理 SQL 不兼容

- 发现时间：2026-07-27
- 模块：核心灰度/测试基线
- 等级：P1
- 现象：从 `backend` 运行全量测试时，多个测试在应用初始化阶段失败：
  `DELETE FROM grayscale_config WHERE config_key NOT IN ?`。
- 根因：当前迁移代码将 tuple 作为单个 bind parameter 传给 SQLite 的 `NOT IN`，
  SQLite 不能展开该参数。
- 影响：68 个 setup error，阻断核心回归；Education 灰度测试也依赖此路径。
- 当前证据：基线结果为 `13 failed, 173 passed, 68 errors`。
- 处理：通过应用初始化 seam 增加回归测试；使用 SQLAlchemy expanding bind 修复
  SQLite/MySQL 的 `NOT IN` 参数；删除启动时强制重新启用全部灰度项的行为。
- 验证：新增回归测试通过；全量测试不再出现灰度迁移 setup error。
- 状态：已解决。

## EDU-BASE-003：前端生产构建超出初始两分钟窗口（已解决）

- 发现时间：2026-07-27
- 模块：前端构建基线
- 等级：P2
- 现象：`npm run build` 在 120 秒窗口内未结束。
- 根因：待检查依赖状态和构建进程；当前未得到编译错误。
- 处理：使用更长的受控窗口重跑，并记录最终退出码；若持续缓慢再定位。
- 处理：确认本地 `node_modules` 缺失 package.json 已声明的 `codemirror` 和
  `vue-codemirror`，补齐本地依赖后重新构建。
- 验证：生产构建成功，仅保留既有 bundle/图片体积警告。
- 状态：已解决。

## EDU-BASE-004：核心全量回归仍有既存失败（已解决）

- 发现时间：2026-07-27
- 模块：核心回归
- 等级：P1
- 现象：灰度迁移修复后，全量后端结果为 `14 failed, 241 passed`。
- 主要分组：
  - 内建 capability 使用的 `tool_search` 分类未能 seed。
  - 一个 OpenCode fallback 输出契约失败。
- 影响：不再阻断应用初始化，但最终兼容回归不能带着这些失败完成。
- 处理：在 Education 基础切片后分别以现有公开测试 seam 定位和修复，不与业务实现混改。
- 处理：将 `rag_search` 的不存在分类 `tool_search` 修正为内建 `tool_web`；OpenCode
  fallback 不再把内部 report card 冒充最终助手回答。
- 验证：后端全量 `263 passed`。
- 状态：已解决。

## EDU-ARCH-001：Education 服务壳不可导入（已解决）

- 发现时间：2026-07-27
- 模块：Education 服务
- 等级：P0
- 现象：`backend/services/edu/app.py` 导入不存在的
  `weagent_core.services.domain_base`，仓库实际包名是 `app`。
- 影响：5102 服务无法启动，所有 Education API 不存在。
- 处理计划：建立可注入 testing config 的 Education app factory，并复用现有
  `app.services.domain_base`，以健康检查和代理 seam 做首个红绿切片。
- 处理：建立可注入配置的 `create_edu_app` 应用工厂，修正核心包导入，复用可注入数据库的
  `DomainServiceBase`，并增加健康、JWT 和双层灰度测试。
- 验证：Education 基础切片与灰度回归 `5 passed`。
- 状态：已解决。

## EDU-SEC-001：现有 Artifact 与 sandbox 文件路由缺少对象级 ACL（已解决）

- 发现时间：2026-07-27
- 模块：核心 Artifact/sandbox
- 等级：P0
- 现象：现有读取和下载主要验证“已登录”，没有完整的 conversation/course/object owner
  校验。
- 影响：Education 的跨学生、跨课程 Artifact 隔离验收无法通过。
- 处理计划：先完成课程成员/发布防火墙，再通过授权 adapter 或核心通用 access policy
  收紧读取；补 ID 猜测和跨用户回归测试。
- 处理：核心 SQL Artifact 增加 owner 字段；创建、读取、更新和按消息列表均校验
  conversation owner/participant，跨用户统一返回 404。Education 发布范围的 Artifact
  仍由 Education 发布 manifest 和课程 membership 继续收口。
- 验证：Artifact ACL 与既有消息/Artifact 合同 `4 passed`。
- 处理：sandbox 的文件树、原始文件、下载、ZIP 导出、workspace 预览、写回和 Agent
  文件接口统一增加 JWT 与会话 owner/participant 校验；未知 session 与跨用户访问统一返回
  404，且在授权失败时不会触达 container manager。
- 验证：核心 Artifact ACL `4 passed`；sandbox 文件权限矩阵 `1 passed`；Education
  真实业务 UAT 完成 22 项跨角色/跨课程/跨学生隔离检查。
- 状态：已解决。

## EDU-RUNTIME-001：工具执行结果没有回送模型

- 发现时间：2026-07-27
- 模块：sandbox Agent runtime
- 等级：P0
- 现象：模型输出 tool call 后服务端执行工具，但结果没有形成同一 provider 的下一轮输入。
- 影响：Agent 无法依据 RAG/搜索结果生成真正的最终回答。
- 处理计划：以 provider/tool 公共合同补完整工具闭环，并保持现有事件和 fallback 兼容。
- 处理：provider 首轮输出 tool call 后，服务端执行注册工具，将结构化结果回送同一
  provider 继续推理；默认最多 4 轮、硬上限 10 轮，并保留事件输出与失败诊断。
- 验证：`test_sandbox_tool_loop.py` 覆盖结果回灌、轮次限制、未知工具与异常路径。
- 状态：已解决。

## EDU-RAG-001：RAG scope 不是服务端授权边界

- 发现时间：2026-07-27
- 模块：RAG
- 等级：P0
- 现象：workspace/domain 主要由调用参数和提示词提供，混合检索关键词分支未完整过滤；
  sandbox 主链也未稳定注入 RAG 内部认证。
- 影响：无法保证教师、课程和学生私有资料隔离。
- 处理计划：服务端构建 scope、RAG 强制过滤、注入最小内部身份并补权限矩阵测试。
- 处理：会话服务从 owner、domain 与受信 workspace 构造 scope 并注入 sandbox；
  `rag_search` 忽略模型传入的扩大范围参数，只接受服务端环境中的 user/domain/workspace
  边界。联网资料链拆为 SearchProvider、SafeWebPageReader、Retriever、Reranker，
  并区分摘要与正文，加入 SSRF、重定向、超时、体积、类型与 fallback 防护。
- 验证：`test_education_rag_scope.py`、`test_conversation_rag_scope.py`、
  `test_education_rag_resource_pipeline.py` 全部通过。
- 状态：已解决。
