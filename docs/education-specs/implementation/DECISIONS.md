# Education MVP 实施决策

## DEC-001：开发阶段连续推进

- 每个工作包执行自动测试、自审、回滚点和灰度验证。
- 阶段完成后自动进入下一工作包，不设置用户审核门。
- 产品运行时的教师发布、反馈和最终成绩审批保持不变。

## DEC-002：测试 seam

设计文档已经确认以下公共 seam，实施以这些 seam 做行为测试：

- 核心领域代理：`/api/domain/edu/*`。
- Education HTTP API：课程、成员、课时、发布、作业、提交、反馈、学情。
- RAG/Search adapter 合同：SearchHit、FetchedDocument、EvidenceChunk。
- Agent/Workflow 合同：版本化输入输出、EducationAgentRun、审批门。
- Artifact：核心 Artifact ID、授权预览和可打开导出文件。
- 前端：真实路由与用户可见教师/学生流程。

不以私有方法、数据库副作用或内部调用次数作为主要验收 seam。

## DEC-003：真实配置与密钥

- 根目录 `.env` 仅通过现有配置加载器使用。
- 不输出、复制、提交或写入 Artifact。
- 常规自动化测试使用确定性 fixture；真实 provider 仅用于集成和最终 UAT。
- UAT 只使用合成账号和自有/开放教学材料。
