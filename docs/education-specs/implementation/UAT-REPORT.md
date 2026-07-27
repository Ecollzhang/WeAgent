# Education MVP UAT 报告

> 本报告只记录脱敏证据。密钥、密码、原始 `.env`、邀请令牌、学生原文和模型原文均未
> 写入日志或仓库。

## 1. 最终验收状态

Education MVP 的真实多用户最小闭环已通过：

- 教师创建并管理高中英语、小学语文两类课程。
- 每门课程均有两名真实独立身份的学生成员。
- 阅读与写作分别建课、编写结构化教案、创建活动并发布。
- 教师发布作业，学生服务端保存/恢复草稿、提交，教师发布反馈。
- 学习事件回流为课程学情，两个课程完成率均为 `1.0`。
- 灰度关闭、对象 ACL、RAG scope 与搜索 fallback 均有自动化证据。

## 2. 验收环境

- 日期：2026-07-27
- 分支：`feature/education`
- Education API：真实 Flask 应用工厂，UAT 使用一次性内存 SQLite，避免污染开发数据。
- Web：生产构建 `frontend/dist`，本地同源 UAT harness 连接真实 Education API。
- 模型：读取仓库根目录已忽略的 `.env`，走 OpenAI-compatible chat completions。
- 外部动作：未部署、未合并、未 push。

## 3. 高中英语标杆课程

- 课程：`高中英语：叙事阅读与写作`
- 学段/类型：`senior_high` / `narrative`
- 课时：阅读 1、写作 1；均含结构化目标、教学阶段、学生任务与教师私有 rubric。
- 作业：阅读证据任务 1、写作证据任务 1。
- 学生：2 人，4 次草稿恢复、4 次提交、4 次反馈。
- 学情：完成率 `1.0`，平均分 `8.5`。

## 4. 小学语文标杆课程

- 课程：`小学语文：寓言阅读与表达`
- 学段/类型：`primary` / `fable`
- 课时：阅读 1、写作 1；按寓言文体组织人物行动、结果、寓意与改写任务。
- 作业：阅读证据任务 1、写作证据任务 1。
- 学生：2 人，4 次草稿恢复、4 次提交、4 次反馈。
- 学情：完成率 `1.0`，平均分 `8.5`。

## 5. 多用户、权限与数据隔离

- 教师 1、学生 2、外部用户 1。
- 真实业务脚本共完成 22 项隔离断言：
  - 外部用户不能查看课程成员、课时发布或作业。
  - 学生发布快照不包含教师 `answer_key`、rubric 或 evaluation。
  - 学生不能读取另一名学生的反馈。
  - 教师角色完全由服务端 course membership 决定。
- SQL Artifact 对会话 owner/participant 校验；跨用户读取、更新和消息列表返回 404。
- sandbox 文件树、原始文件、下载、ZIP、预览与写回同样校验会话
  owner/participant；授权失败不会触达 container manager。

## 6. Agent、RAG、联网搜索与 fallback

- 教师侧、学生侧和内部 Worker 共 9 个 Education Agent 合同。
- 8 个可模板化工作流支持 strict/guided DAG，自建流程禁止循环和任意代码，并保留
  教师发布审批门。
- tool call 结果会回送同一 provider 继续推理，默认 4 轮、最大 10 轮。
- RAG scope 由服务端基于 user/domain/workspace 注入，模型参数不能扩大范围。
- 联网链路为 `SearchProvider → SafeWebPageReader → Retriever → Reranker`。
- 搜索摘要不当作网页全文；读取失败可切换候选 URL/provider，全部失败时返回可诊断
  fallback，不伪造正文。
- SSRF、重定向、私网地址、超时、响应体积与内容类型均有回归测试。

## 7. 真实模型与浏览器 UAT

真实模型调用的脱敏证据：

- provider：`openai-compatible`
- HTTP：`200`
- 返回模型标识：`deepseek-v4-flash`
- 输出长度：`1155`
- 输出 SHA-256 前 12 位：`6fdb6c6b35b4`

浏览器在生产构建上完成：

1. 使用一次性本地 UAT 身份进入 `/education`。
2. 正确显示高中英语和小学语文两张课程卡及教师身份。
3. 通过真实表单创建 `UAT 新建高中英语课程`。
4. 自动进入课程空间，成功切换到成员页并读取教师成员数据。
5. 浏览器 session、一次性数据库与本地服务进程在验收后关闭。

## 8. 自动化回归

- 后端全量：`302 passed`。
- Education API/Agent/RAG 定向测试：通过。
- sandbox 文件 ACL：`1 passed`。
- 前端合同与 Vue 编译测试：`8 passed`。
- 前端生产构建：成功；仅有既有 bundle/图片体积警告。
- UAT 脚本：`backend/scripts/education_uat.py`。
- 浏览器 harness：`backend/scripts/education_browser_uat_server.py`。

## 9. 已知 P2

- 后端测试需从 `backend` 目录运行，仓库根目录未设置 `app` 的 Python import path。
- 当前 Windows Conda profile 激活会在测试结束后输出 GBK 编码噪声；pytest/UAT 子进程
  本身退出码与结果不受影响。
- 前端生产构建保留既有 bundle 与图片体积警告，不阻断 MVP。
