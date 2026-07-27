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

## EDU-BASE-003：前端生产构建超出初始两分钟窗口

- 发现时间：2026-07-27
- 模块：前端构建基线
- 等级：P2
- 现象：`npm run build` 在 120 秒窗口内未结束。
- 根因：待检查依赖状态和构建进程；当前未得到编译错误。
- 处理：使用更长的受控窗口重跑，并记录最终退出码；若持续缓慢再定位。
- 状态：调查中。

## EDU-BASE-004：核心全量回归仍有既存失败

- 发现时间：2026-07-27
- 模块：核心回归
- 等级：P1
- 现象：灰度迁移修复后，全量后端结果为 `14 failed, 241 passed`。
- 主要分组：
  - 内建 capability 使用的 `tool_search` 分类未能 seed。
  - 一个 OpenCode fallback 输出契约失败。
- 影响：不再阻断应用初始化，但最终兼容回归不能带着这些失败完成。
- 处理：在 Education 基础切片后分别以现有公开测试 seam 定位和修复，不与业务实现混改。
- 状态：待处理。

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

## EDU-SEC-001：现有 Artifact 与 sandbox 文件路由缺少对象级 ACL

- 发现时间：2026-07-27
- 模块：核心 Artifact/sandbox
- 等级：P0
- 现象：现有读取和下载主要验证“已登录”，没有完整的 conversation/course/object owner
  校验。
- 影响：Education 的跨学生、跨课程 Artifact 隔离验收无法通过。
- 处理计划：先完成课程成员/发布防火墙，再通过授权 adapter 或核心通用 access policy
  收紧读取；补 ID 猜测和跨用户回归测试。
- 状态：待处理。

## EDU-RUNTIME-001：工具执行结果没有回送模型

- 发现时间：2026-07-27
- 模块：sandbox Agent runtime
- 等级：P0
- 现象：模型输出 tool call 后服务端执行工具，但结果没有形成同一 provider 的下一轮输入。
- 影响：Agent 无法依据 RAG/搜索结果生成真正的最终回答。
- 处理计划：以 provider/tool 公共合同补完整工具闭环，并保持现有事件和 fallback 兼容。
- 状态：待处理。

## EDU-RAG-001：RAG scope 不是服务端授权边界

- 发现时间：2026-07-27
- 模块：RAG
- 等级：P0
- 现象：workspace/domain 主要由调用参数和提示词提供，混合检索关键词分支未完整过滤；
  sandbox 主链也未稳定注入 RAG 内部认证。
- 影响：无法保证教师、课程和学生私有资料隔离。
- 处理计划：服务端构建 scope、RAG 强制过滤、注入最小内部身份并补权限矩阵测试。
- 状态：待处理。
