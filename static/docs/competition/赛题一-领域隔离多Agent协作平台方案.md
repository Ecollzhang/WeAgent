# 赛题一：领域隔离多Agent协作平台 — 参赛方案

> **赛题**：生成式大语言模型与智能体
> **大赛主题**：AI赋能 智行致远
> **参赛类别**：开放命题 — 技术创新类
> **项目名称**：WeAgent Domain — 面向行政办公、教学与学习的领域隔离多智能体协作平台

---

## 目录

1. [项目概述与赛题契合度](#1-项目概述与赛题契合度)
2. [现有基础评估](#2-现有基础评估)
3. [可行性分析](#3-可行性分析)
4. [创新点分析](#4-创新点分析)
5. [竞争力分析](#5-竞争力分析)
6. [技术方案详细设计](#6-技术方案详细设计)
7. [产品设计](#7-产品设计)
8. [实施计划](#8-实施计划)
9. [风险与对策](#9-风险与对策)
10. [预期成果与展示方案](#10-预期成果与展示方案)

---

## 1. 项目概述与赛题契合度

### 1.1 项目一句话简介

**WeAgent Domain** 是在已有成熟多Agent协作平台基础上，构建的面向行政办公、教学、学习三大场景的**领域知识隔离、Agent团队专配、能力按需组装**的垂直智能体协作解决方案。

### 1.2 核心命题

当前通用大模型和Agent平台存在一个关键矛盾：**通用性越强，领域专业性越弱**。一个既能写代码、又能写公文、还能备课的Agent，在每个领域都只能是"及格"水平。真实场景中：

- **行政办公**需要理解公文规范、审批流程、红头文件格式
- **教学**需要掌握课程标准、教学设计方法论、学情分析框架
- **学习**需要知识图谱导航、自适应练习、错因诊断

本项目提出"**领域隔离Agent协作平台**"概念——将同一个多Agent协作引擎，按领域封装为独立的"Agent工作空间"，每个空间拥有专属的Agent团队、知识库、工具集和工作流模板，实现**领域内深度专业、领域间完全隔离、底层引擎统一复用**。

### 1.3 与大赛主题的契合度

| 大赛要求 | 本项目对应 |
|---|---|
| **AI赋能** | 以大模型为引擎，Agent为执行体，赋能办公、教学、学习三大真实场景 |
| **智行致远** | 多Agent协作体现"智"，领域隔离+自动调度体现"行"，可落地可扩展体现"致远" |
| **生成式大语言模型** | Claude Code/Codex/OpenCode多引擎驱动，LLM负责理解、规划、生成 |
| **智能体** | 主持Agent+Worker Agent双层调度，感知环境、自主决策、协作执行 |
| **场景驱动** | 三个领域均有明确场景：公文处理工作流、教学设计→课件生成→作业批改闭环、个性化学习路径 |
| **技术创新** | 领域隔离架构、可插拔能力包、双循环教学-学习生态 |
| **应用落地** | 可部署于学校、培训机构、中小型办公室，具备明确应用价值 |

---

## 2. 现有基础评估

### 2.1 WeAgent 已完成的能力矩阵

| 能力维度 | 已实现内容 | 成熟度 |
|---|---|---|
| **多Agent协作调度** | 主持Agent+Worker Agent双层模型，JSON任务计划解析，并行/串行调度 | ★★★★★ |
| **Docker沙箱隔离** | 以conversation为粒度的容器隔离，文件系统、工具环境、服务端口完全独立 | ★★★★★ |
| **多引擎适配** | Claude Code、Codex、OpenCode三引擎统一工厂模式接入，动态切换 | ★★★★☆ |
| **实时事件系统** | Socket.IO推送，SandboxEventBridge事件桥接，消息元素结构化持久化 | ★★★★☆ |
| **能力/工具系统** | Capability导入、版本管理、安全审计、Agent绑定、会话级投影 | ★★★★☆ |
| **多端客户端** | Web (Vue 2.7)、Electron桌面端、Capacitor Android端 | ★★★★☆ |
| **产物体系** | 代码、网页、文档、表格、图片、Diff等多类型结构化产物，在线预览编辑 | ★★★★☆ |
| **服务预览** | Docker内服务启动→宿主机端口代理→前端iframe预览 | ★★★☆☆ |
| **Agent类别系统** | 5大类别（文档/编程/测试/设计/数据分析），种子Agent预设 | ★★★☆☆ |
| **用户与权限** | JWT认证，多用户隔离，会话级权限控制 | ★★★☆☆ |

### 2.2 可直接复用的核心资产

1. **完整的多Agent调度引擎**（`message_service.py` 109KB, `orchestrator.py` 82KB）：无需重新开发调度逻辑
2. **Docker沙箱基础设施**（`manager.py` 73KB, Dockerfile, 容器镜像）：隔离执行环境直接可用
3. **Provider Adapter工厂**（3种引擎适配器）：大模型接入层已完成
4. **前端ChatWindow+ArtifactWorkbench**（合计134KB）：核心交互界面可直接复用
5. **Capability能力系统**（导入、版本、审计、绑定、投影）：领域工具的安装和管理基础设施完备
6. **Socket.IO实时通道**：前后端实时通信无需重建

### 2.3 需要新增的能力

| 需要新增 | 说明 | 工作量估计 |
|---|---|---|
| **Workspace领域空间** | 新增workspace概念，作为领域隔离的顶层容器 | 中 |
| **领域知识库(RAG)** | 每个领域独立的知识检索增强生成系统 | 中-高 |
| **领域Agent模板** | 三个领域预设的Agent团队配置（角色、技能、工具） | 低-中 |
| **领域能力包** | 办公/教学/学习场景的专用工具、MCP、Skill集合 | 中 |
| **领域工作流模板** | 预设的多Agent协作流程（如公文审批流、教学设计流） | 中 |
| **领域切换UI** | 前端workspace选择器、领域仪表盘 | 低-中 |
| **跨域数据桥** | 教学→学习的数据传递（如教师布置作业→学生接收） | 中 |

---

## 3. 可行性分析

### 3.1 技术可行性：★★★★★（非常高）

**结论：架构天然支持，改动以增量为主，无需重构核心系统。**

| 维度 | 分析 |
|---|---|
| **架构兼容性** | 现有Agent类别(category)系统已具备领域分类的雏形；Capability绑定机制天然支持"领域→Agent→工具"的映射链；Docker按conversation隔离的机制无需改动 |
| **数据库扩展** | 新增Workspace表和相关关联表（约3-4张表），对现有16张表无破坏性修改。Workspace可视为conversation的上层分组容器 |
| **调度引擎复用** | 核心的Moderator→Worker调度逻辑（`message_service.py` _dispatch_agent_sandbox）完全不需改动，只需在Workspace层面配置不同Agent团队 |
| **前端改造** | ChatWindow组件可直接复用，新增Workspace选择器和领域仪表盘约2-3个新视图 |
| **风险点可控** | 知识库(RAG)是最大的新增模块，但属于独立子系统，不影响现有核心链路 |

### 3.2 场景可行性：★★★★☆（高）

| 领域 | 场景可行性 | 依据 |
|---|---|---|
| **行政办公** | 高 | 公文撰写、会议纪要、报表生成、邮件起草均为LLM擅长的文本生成任务；Agent协作模式明确（起草→审核→修订→定稿） |
| **教学** | 高 | 教学设计、课件制作、习题生成已有成熟的教育AI实践；多Agent可分工（课程设计Agent+课件制作Agent+评估Agent） |
| **学习** | 中-高 | 个性化学习路径需较多领域知识积累；但笔记整理、知识问答、代码练习等功能可直接实现 |

### 3.3 资源可行性：★★★★☆（高）

- **算力**：复用现有Docker沙箱机制，每个会话一个容器，资源需求与当前一致
- **模型API**：现有三引擎适配器已封装好，无需额外对接
- **开发人力**：基于成熟平台增量开发，1-2人2-3个月可完成核心功能
- **数据**：三个领域的知识库可基于公开资源（政府公文规范、课标、教材目录）构建初始版本

### 3.4 综合可行性判断

**该项目高度可行。** 核心原因：不是从零开始构建Agent平台，而是在一个已经过完整工程验证的多Agent协作系统上，新增领域隔离层和领域专用能力包。技术风险主要集中在RAG知识库的质量和领域工具的丰富度上，不影响核心Agent调度链路的稳定性。

---

## 4. 创新点分析

### 4.1 核心创新：领域隔离的Agent协作空间（Domain-Isolated Agent Workspace）

**业界对比**：

| 方案 | 模式 | 问题 |
|---|---|---|
| ChatGPT/Claude | 单Agent对话 | 无协作，无隔离 |
| AutoGPT/MetaGPT | 多Agent，单一空间 | 不同任务共享上下文，角色混淆 |
| Coze/Dify | 工作流+知识库 | 非真正的多Agent自主协作 |
| **WeAgent Domain** | **领域隔离 + 多Agent协作** | **每个领域专属Agent团队+知识库+工具，领域间完全隔离** |

**创新本质**：将"一个通用大模型做所有事"转变为"多个专业Agent团队各司其职"。类似于微服务架构对单体的改造——不是让一个Agent变全能，而是让合适的Agent团队处理合适的领域任务。

### 4.2 创新点二：可插拔的领域能力包（Pluggable Domain Capability Package）

将每个领域的能力（Agent角色定义、System Prompt、工具集、MCP服务、知识库、工作流模板）打包为**独立安装和切换的能力包**：

```
Domain Capability Package
├── agents/           # 领域专属Agent定义
│   ├── moderator.md  # 领域主持Agent系统提示词
│   └── workers/      # Worker Agent角色定义
├── knowledge/        # 领域知识库(RAG向量库)
├── tools/            # 领域专用工具
├── workflows/        # 预设工作流模板
└── manifest.json     # 能力包清单
```

用户切换领域 = 切换一整套Agent协作环境，而非仅切换一个提示词。这比Dify/Coze的知识库+工作流模式更彻底——连Agent团队构成和执行策略都随领域改变。

### 4.3 创新点三：教育场景的"教学-学习"双循环生态

在三大领域中，**教学平台和学习平台天然形成闭环**：

```
教师(教学平台)                    学生(学习平台)
   │                                  │
   设计课程 ────→ 发布作业 ────→ 接收作业
   │                                  │
   查看学情 ←──── 提交情况 ←──── 完成练习
   │                                  │
   调整教学 ←──── 数据分析 ←──── 错题记录
```

这是其他Agent平台不具备的独特优势——**教学者和学习者使用同一个底层平台的不同领域空间，通过跨域数据桥实现教学反馈闭环**。这种"教学相长"的生态叙事，在AI教育类参赛作品中具有强区分度。

### 4.4 创新点四：角色边界强制的安全协作

现有系统已有的`_role_boundary_prompt()`机制（`orchestrator.py` L532-555），在每个Worker Agent执行前注入角色边界约束。这在领域隔离场景下更进一步：

- 公文撰写Agent不能调用代码执行工具
- 学情分析Agent不能修改课程内容
- 学习者的Agent不能访问教师的知识库

这种**能力边界的显式执行**（不仅是prompt层面的建议，还包括工具/文件/网络的访问控制清单），使多Agent协作在专业场景中更可信。

### 4.5 创新点五：从"AI工具"到"AI同事"的协作范式

行政办公场景中的Agent团队模拟真实办公协作关系：

| 真实办公角色 | Agent对应 |
|---|---|
| 办公室主任(审核) | Moderator Agent (任务分配+质量把关) |
| 文秘(起草) | 公文撰写Agent |
| 数据分析员 | 报表分析Agent |
| 会议记录员 | 会议纪要Agent |

用户不是给AI下达指令，而是像管理一个微型团队一样与Agent团队协作——这是从"工具使用"到"团队协作"的范式升级。

---

## 5. 竞争力分析

### 5.1 与典型参赛项目的对比

| 维度 | 典型参赛项目 | WeAgent Domain | 优势 |
|---|---|---|---|
| **起点** | 从零搭建Demo | 成熟工程平台升级 | 功能完整度、稳定性远超Demo级别 |
| **Agent模型** | 单Agent或简单多Agent | 主持+Worker双层调度+领域隔离 | 调度复杂度高一个量级 |
| **执行环境** | 本地进程或无隔离 | Docker沙箱完全隔离 | 安全性和可复现性强 |
| **引擎选择** | 单一API | Claude/Codex/OpenCode三引擎 | 不被单一厂商锁定 |
| **产物交付** | 纯文本回复 | 代码/网页/文档/表格/PPT/服务预览 | 交付物丰富度碾压 |
| **客户端** | 仅Web | Web+Desktop+Android | 使用场景更广 |
| **领域深度** | 通用聊天 | 办公/教学/学习领域知识+工具 | 解决真问题 |
| **可展示性** | PPT/Demo视频 | 可直接操作的真实系统 | 评委可上手体验 |

### 5.2 核心竞争力总结

1. **技术护城河深**：多Agent调度+Docker沙箱+多引擎适配+实时事件系统，四个子系统已完整实现并协同工作，非短期能复制
2. **场景叙事强**：行政办公+教学+学习三个场景覆盖广泛的用户群体，且有"教学-学习"双循环的独特生态故事
3. **展示效果好**：评委可以实际注册使用，创建会话，看到Agent实时协作的过程（进度条、工作流图、产物逐步生成），而非静态PPT
4. **落地潜力大**：学校/培训机构/中小企业办公是真实存在且体量庞大的市场
5. **扩展性明确**：领域能力包的插拔架构意味着可以在比赛中和比赛后持续扩展新领域（智慧医疗、智慧城市、数字文旅等）

### 5.3 差异化定位

**我们不做一个"更好的ChatGPT"，而是做一个"领域专属的AI团队协作空间"。**

这个定位避开了与大厂通用AI助手的正面竞争，切入了他们覆盖薄弱的"垂直场景多Agent协作"赛道。

---

## 6. 技术方案详细设计

### 6.1 总体架构

```
┌──────────────────────────────────────────────────────┐
│                    多端客户端层                         │
│   Web (Vue 2.7)  │  Desktop (Electron)  │  Android    │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP REST + Socket.IO
┌──────────────────────▼───────────────────────────────┐
│                 Flask 后端控制面                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │ Auth     │ │Workspace │ │ Domain Capability    │  │
│  │ Service  │ │Service   │ │ Package Manager      │  │
│  └──────────┘ └──────────┘ └──────────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────┐  │
│  │Message   │ │Sandbox   │ │ Knowledge Base       │  │
│  │Service   │ │Manager   │ │ Service (RAG)        │  │
│  └──────────┘ └──────────┘ └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐ │
│  │              MySQL + Redis + Milvus              │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────────────┘
                       │ Docker API
┌──────────────────────▼───────────────────────────────┐
│             Docker Sandbox 容器集群                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ Office      │  │ Teaching     │  │ Learning    │  │
│  │ Container   │  │ Container    │  │ Container   │  │
│  │             │  │              │  │             │  │
│  │ Moderator   │  │ Moderator    │  │ Moderator   │  │
│  │ ┌─────────┐ │  │ ┌──────────┐ │  │ ┌─────────┐ │  │
│  │ │公文Agent │ │  │ │课程Agent │ │  │ │笔记Agent│ │  │
│  │ │报表Agent │ │  │ │课件Agent │ │  │ │练习Agent│ │  │
│  │ │会议Agent │ │  │ │评估Agent │ │  │ │导师Agent│ │  │
│  │ └─────────┘ │  │ └──────────┘ │  │ └─────────┘ │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  │
│  每个会话 = 一个独立Docker容器                          │
│  容器内 = 一个领域专属Agent团队 + 领域工具 + 领域知识     │
└──────────────────────────────────────────────────────┘
```

### 6.2 核心概念模型

#### 6.2.1 Workspace（领域工作空间）— 新增核心概念

```sql
-- 新增表：workspaces
CREATE TABLE workspaces (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    domain VARCHAR(50) NOT NULL,          -- 'office', 'teaching', 'learning'
    name VARCHAR(200) NOT NULL,
    description TEXT,
    config JSON,                          -- 领域配置（Agent团队、知识库、工具集）
    capability_package_version VARCHAR(50), -- 绑定的能力包版本
    knowledge_base_ids JSON,              -- 关联的知识库ID列表
    status ENUM('active','archived') DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_domain (domain),
    INDEX idx_user_domain (user_id, domain)
);

-- 扩展现有conversations表，新增workspace_id
ALTER TABLE conversations ADD COLUMN workspace_id VARCHAR(36);
ALTER TABLE conversations ADD FOREIGN KEY (workspace_id) REFERENCES workspaces(id);
```

#### 6.2.2 Domain Capability Package（领域能力包）

```sql
-- 新增表：domain_capability_packages
CREATE TABLE domain_capability_packages (
    id VARCHAR(36) PRIMARY KEY,
    domain VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    version VARCHAR(50) NOT NULL,
    manifest JSON NOT NULL,              -- 包清单（agents, tools, workflows, knowledge）
    agent_templates JSON,                -- Agent模板定义
    tool_definitions JSON,               -- 工具定义
    workflow_templates JSON,             -- 工作流模板
    knowledge_base_config JSON,          -- 知识库配置
    status ENUM('draft','published','deprecated') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 6.2.3 Knowledge Base（领域知识库）

```sql
-- 新增表：knowledge_bases
CREATE TABLE knowledge_bases (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    vector_store_type VARCHAR(50) DEFAULT 'milvus', -- 向量数据库类型
    collection_name VARCHAR(200),                   -- Milvus集合名
    document_count INT DEFAULT 0,
    status ENUM('building','ready','error') DEFAULT 'building',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
);
```

### 6.3 领域能力包设计

#### 6.3.1 行政办公领域能力包 (office/v1)

```json
{
  "domain": "office",
  "name": "行政办公智能协作包",
  "version": "1.0.0",
  "agents": {
    "moderator": {
      "name": "办公协调员",
      "system_prompt": "你是行政办公团队的协调员。根据用户需求，将任务分配给公文撰写、报表分析、会议管理等专业Agent...",
      "adapter": "claude"
    },
    "workers": [
      {
        "id": "doc_writer",
        "name": "公文撰写助手",
        "skill": "document",
        "system_prompt": "你是专业的公文撰写助手。熟悉党政机关公文格式(GB/T 9704-2012)，能撰写通知、报告、请示、函等各类公文...",
        "tools": ["docx_generator", "template_library", "format_checker"]
      },
      {
        "id": "report_analyst",
        "name": "报表分析助手",
        "skill": "data",
        "system_prompt": "你是行政数据报表分析助手。能解读Excel/CSV数据，生成统计报表、趋势分析和可视化图表...",
        "tools": ["excel_reader", "chart_generator", "data_summarizer"]
      },
      {
        "id": "meeting_assistant",
        "name": "会议纪要助手",
        "skill": "document",
        "system_prompt": "你是会议纪要整理专家。能从会议录音转写文本中提取关键决议、行动项和责任人...",
        "tools": ["transcript_parser", "action_tracker", "minutes_template"]
      },
      {
        "id": "email_drafter",
        "name": "邮件起草助手",
        "skill": "document",
        "system_prompt": "你是商务邮件起草助手。根据场景撰写正式邮件、通知邮件、汇报邮件等...",
        "tools": ["email_template", "tone_adjuster"]
      }
    ]
  },
  "workflows": [
    {
      "id": "document_approval",
      "name": "公文起草→审核→修订→定稿",
      "steps": [
        {"agent": "doc_writer", "action": "起草初稿"},
        {"agent": "moderator", "action": "审核格式与内容"},
        {"agent": "doc_writer", "action": "根据审阅意见修订"},
        {"agent": "moderator", "action": "最终确认输出"}
      ]
    },
    {
      "id": "meeting_management",
      "name": "会议全流程管理",
      "steps": [
        {"agent": "meeting_assistant", "action": "生成会议议程"},
        {"agent": "moderator", "action": "确认议程"},
        {"agent": "meeting_assistant", "action": "整理会议纪要"},
        {"agent": "email_drafter", "action": "发送会议纪要邮件"}
      ]
    }
  ],
  "knowledge": {
    "collections": ["gov_document_standards", "office_templates", "regulations"]
  }
}
```

#### 6.3.2 教学领域能力包 (teaching/v1)

```json
{
  "domain": "teaching",
  "name": "教学智能协作包",
  "version": "1.0.0",
  "agents": {
    "moderator": {
      "name": "教学设计师",
      "system_prompt": "你是教学设计协调员。根据教师的课程需求，组织课程设计、课件制作、习题生成和学情分析Agent协作完成教学任务...",
      "adapter": "claude"
    },
    "workers": [
      {
        "id": "course_designer",
        "name": "课程设计助手",
        "skill": "design",
        "system_prompt": "你是课程教学设计专家。熟悉Bloom教育目标分类法、逆向教学设计(UbD)等方法论，能设计教学目标、教学活动和评估方案...",
        "tools": ["curriculum_analyzer", "syllabus_generator", "learning_objective_designer"]
      },
      {
        "id": "courseware_maker",
        "name": "课件制作助手",
        "skill": "design",
        "system_prompt": "你是课件制作专家。能将教学设计转化为结构清晰、视觉美观的PPT/网页课件，包含互动元素...",
        "tools": ["ppt_generator", "html_courseware", "diagram_drawer", "interactive_quiz_embedder"]
      },
      {
        "id": "quiz_generator",
        "name": "习题生成助手",
        "skill": "data",
        "system_prompt": "你是习题设计专家。能根据教学目标和知识点自动生成选择题、填空题、简答题、案例分析题等多种题型的练习题...",
        "tools": ["question_bank", "difficulty_calibrator", "knowledge_point_mapper"]
      },
      {
        "id": "learning_analyst",
        "name": "学情分析师",
        "skill": "data",
        "system_prompt": "你是学情数据分析师。能分析学生成绩、作业完成情况、课堂参与度等数据，输出学情报告和教学建议...",
        "tools": ["grade_analyzer", "progress_tracker", "report_generator"]
      }
    ]
  },
  "workflows": [
    {
      "id": "lesson_preparation",
      "name": "备课全流程",
      "steps": [
        {"agent": "course_designer", "action": "设计教学目标与活动"},
        {"agent": "courseware_maker", "action": "制作教学课件"},
        {"agent": "quiz_generator", "action": "生成课堂练习与课后作业"},
        {"agent": "moderator", "action": "审核备课成果"}
      ]
    },
    {
      "id": "exam_analysis",
      "name": "考试分析与教学调整",
      "steps": [
        {"agent": "learning_analyst", "action": "分析考试成绩数据"},
        {"agent": "course_designer", "action": "根据分析结果调整教学计划"},
        {"agent": "quiz_generator", "action": "针对薄弱知识点生成补救练习"}
      ]
    }
  ],
  "knowledge": {
    "collections": ["curriculum_standards", "teaching_methods", "subject_knowledge"]
  }
}
```

#### 6.3.3 学习领域能力包 (learning/v1)

```json
{
  "domain": "learning",
  "name": "学习智能协作包",
  "version": "1.0.0",
  "agents": {
    "moderator": {
      "name": "学习规划师",
      "system_prompt": "你是学习规划协调员。根据学生的学习目标、当前水平和时间安排，协调各学习Agent制定和执行个性化学习计划...",
      "adapter": "claude"
    },
    "workers": [
      {
        "id": "knowledge_navigator",
        "name": "知识导航员",
        "skill": "document",
        "system_prompt": "你是学科知识导航专家。能构建知识图谱，诊断学生的知识盲区，推荐学习路径...",
        "tools": ["knowledge_graph", "prerequisite_analyzer", "learning_path_planner"]
      },
      {
        "id": "note_organizer",
        "name": "笔记整理助手",
        "skill": "document",
        "system_prompt": "你是笔记整理专家。能将零散的学习笔记、课堂记录、阅读材料整理为结构化的知识笔记，生成思维导图...",
        "tools": ["note_structurer", "mindmap_generator", "flash_card_maker"]
      },
      {
        "id": "practice_coach",
        "name": "练习教练",
        "skill": "code",
        "system_prompt": "你是练习教练。提供针对性练习题，实时反馈答案，解释错误原因，调整练习难度...",
        "tools": ["adaptive_quiz", "code_practice_env", "mistake_analyzer"]
      },
      {
        "id": "project_mentor",
        "name": "项目导师",
        "skill": "code",
        "system_prompt": "你是项目实践导师。指导学生完成编程项目、实验设计、论文写作等实践性学习任务...",
        "tools": ["code_reviewer", "project_scaffolder", "paper_feedback"]
      }
    ]
  },
  "workflows": [
    {
      "id": "personalized_learning",
      "name": "个性化学习路径",
      "steps": [
        {"agent": "knowledge_navigator", "action": "诊断知识水平与盲区"},
        {"agent": "moderator", "action": "制定学习计划"},
        {"agent": "note_organizer", "action": "整理学习材料"},
        {"agent": "practice_coach", "action": "生成练习题并评估"},
        {"agent": "knowledge_navigator", "action": "更新知识图谱"}
      ]
    },
    {
      "id": "project_practice",
      "name": "项目实践指导",
      "steps": [
        {"agent": "project_mentor", "action": "项目需求分析与设计"},
        {"agent": "project_mentor", "action": "代码编写与调试"},
        {"agent": "project_mentor", "action": "代码审查与优化建议"},
        {"agent": "moderator", "action": "项目总结与知识点回顾"}
      ]
    }
  ],
  "knowledge": {
    "collections": ["subject_knowledge_graph", "exercise_bank", "learning_resources"]
  }
}
```

### 6.4 RAG知识库架构

```
┌─────────────────────────────────────────────┐
│             Knowledge Base Service           │
│  ┌───────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Document  │ │ Chunking │ │ Embedding  │  │
│  │ Ingest    │ │ Strategy │ │ (BGE/M3E)  │  │
│  └───────────┘ └──────────┘ └────────────┘  │
│  ┌──────────────────────────────────────┐    │
│  │        Milvus Vector Store           │    │
│  │  ┌─────────┐ ┌────────┐ ┌────────┐  │    │
│  │  │ office  │ │teaching│ │learning│  │    │
│  │  │collection│ │collect.│ │collect.│  │    │
│  │  └─────────┘ └────────┘ └────────┘  │    │
│  └──────────────────────────────────────┘    │
│  ┌──────────────────────────────────────┐    │
│  │        Retrieval + Rerank            │    │
│  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

每个领域的知识库以独立的Milvus Collection存储，在容器创建时按Workspace所属领域注入对应的知识库检索工具。

### 6.5 跨域数据桥（教学↔学习闭环）

```
┌──────────────────────────────────────────────┐
│            Cross-Domain Data Bridge           │
│                                               │
│  Teaching Workspace ──── publish ────→ Learning Workspace
│  (教师)                                      (学生)
│                                               │
│  - 发布作业/任务                              │
│  - 共享课程材料        ←── submit ───         │
│  - 查看学情报告                               │
│                                               │
│  publish: 作业ID, 内容, 截止时间, 评分标准      │
│  submit:  学生ID, 作业ID, 答案, 完成时间        │
│  feedback: 分数, 评语, 错题分析, 改进建议       │
└──────────────────────────────────────────────┘
```

跨域数据桥通过一个轻量的发布-订阅机制实现，教学Workspace发布的内容可以被指定学习Workspace订阅和接收。这不需要复杂的集成，本质上是一个"作业→完成→批改→反馈"的异步消息通道。

### 6.6 API设计（新增核心接口）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/workspaces` | 创建领域工作空间 |
| GET | `/api/workspaces` | 获取用户的所有工作空间 |
| GET | `/api/workspaces/{id}` | 获取工作空间详情 |
| PUT | `/api/workspaces/{id}` | 更新工作空间配置 |
| DELETE | `/api/workspaces/{id}` | 归档工作空间 |
| POST | `/api/workspaces/{id}/conversations` | 在工作空间中创建会话 |
| GET | `/api/workspaces/{id}/conversations` | 获取工作空间下的会话列表 |
| GET | `/api/domains` | 获取可用领域列表 |
| GET | `/api/domains/{domain}/capability-package` | 获取领域能力包详情 |
| POST | `/api/knowledge-bases/{id}/documents` | 上传文档到知识库 |
| GET | `/api/knowledge-bases/{id}/documents` | 获取知识库文档列表 |
| POST | `/api/knowledge-bases/{id}/search` | 检索知识库 |
| POST | `/api/bridge/assignments` | 教师发布作业（跨域） |
| GET | `/api/bridge/assignments` | 学生获取作业列表 |
| POST | `/api/bridge/assignments/{id}/submit` | 学生提交作业 |

### 6.7 前端改造设计

```
现有路由结构：
  /login  /register  /dashboard  /agents  /settings  /tools  /favorites

新增/改造路由：
  /workspaces              → WorkspaceList.vue     (工作空间列表)
  /workspaces/:id          → WorkspaceDetail.vue   (工作空间详情+会话列表)
  /workspaces/:id/chat/:cid → Dashboard.vue (改造) (聊天界面，注入领域上下文)
  /marketplace             → DomainMarketplace.vue  (领域能力包市场)
  /bridge                  → CrossDomainBridge.vue  (跨域数据桥，教学↔学习)
```

前端核心改造点：
1. **Workspace选择器**：侧边栏顶部新增工作空间下拉切换
2. **领域仪表盘**：每个领域有不同的首页（办公-待办事项，教学-课程列表，学习-学习进度）
3. **领域主题色**：办公(蓝)、教学(绿)、学习(紫)，UI跟随领域变化
4. **Agent面板**：创建会话时，Agent列表按领域过滤（只显示当前领域的Agent模板）

---

## 7. 产品设计

### 7.1 产品定位

**一句话定位**：WeAgent Domain = 领域专属AI团队协作空间，让每个人拥有自己的AI办公团队、AI教学团队或AI学习团队。

**核心价值主张**：
- 对**行政人员**：你的AI文秘+数据分析员+会议助理，懂公文规范，熟悉办公流程
- 对**教师**：你的AI教学设计+课件制作+习题生成+学情分析团队，从备课到评估全流程覆盖
- 对**学生**：你的AI知识导航+笔记整理+练习教练+项目导师，个性化陪伴式学习

### 7.2 用户旅程

#### 场景一：行政办公 — 从会议到公文的全流程

```
1. 小李打开WeAgent，切换到"行政办公"工作空间
2. 上传会议录音转写文本
3. 发送消息："整理这次项目启动会的会议纪要，列出决议事项和负责人"
4. 主持Agent(办公协调员)分析任务 → 分配给会议纪要Agent
5. 会议纪要Agent提取关键信息 → 生成结构化纪要（决议、行动项、责任人、时间节点）
6. 主持Agent审核 → 确认无误，输出纪要文档
7. 小李："根据会议纪要，起草一份项目启动通知，发给全部门"
8. 主持Agent → 分配给公文撰写Agent
9. 公文撰写Agent：参照公文格式规范 → 生成通知初稿
10. 主持Agent审核格式 → 修订 → 输出正式通知
11. 小李："再生成一份项目进度跟踪表模板"
12. 报表分析Agent生成Excel跟踪表 → 小李下载使用
```

#### 场景二：教学 — 一堂课的完整备课

```
1. 王老师切换到"教学"工作空间
2. 输入："我要准备一堂初中物理'浮力'的公开课，45分钟，学生基础一般"
3. 主持Agent(教学设计师)分析需求 → 制定计划：
   - 课程设计Agent：设计教学目标、重难点、教学活动
   - 课件制作Agent：制作互动PPT
   - 习题生成Agent：设计课堂练习和课后作业
4. 三个Worker Agent并行工作
5. 王老师查看并调整课件 → "把阿基米德实验的动画改成交互式模拟"
6. 课件Agent修改 → 输出HTML交互课件（容器内可预览）
7. 王老师确认满意 → 发布作业到学生端
8. 课后查看学情分析 → 学情分析师输出班级掌握情况报告
```

#### 场景三：学习 — 个性化编程学习路径

```
1. 小明切换到"学习"工作空间
2. 输入："我想系统学习Python数据分析，目前只会基础语法"
3. 主持Agent(学习规划师)启动个性化学习流程：
   - 知识导航员：诊断当前水平 → 分析知识图谱 → 推荐学习路径
   - 笔记整理助手：整理学习路径为结构化笔记
4. 小明看到学习路径：NumPy基础 → Pandas → Matplotlib → 实战项目
5. 开始学习NumPy → 练习教练生成适配题目
6. 小明做题 → 错了一道 → 练习教练解释错误原因，生成类似题目巩固
7. 完成学习后 → 项目导师启动实战项目（股票数据分析）
8. 项目导师指导代码编写、审查、优化 → 小明完成第一个数据分析项目
```

### 7.3 界面设计要点

**工作空间选择器（侧边栏顶部）**：
```
┌─────────────────────────┐
│ 🏢 行政办公        ▼   │
│ ─────────────────────  │
│ ○ 🏢 行政办公          │
│ ○ 📚 教学              │
│ ○ 🎓 学习              │
│ ─────────────────────  │
│ + 创建新工作空间        │
└─────────────────────────┘
```

**领域会话创建对话框**：
```
┌─────────────────────────────────────┐
│  创建会话 - 教学空间                 │
│                                     │
│  会话名称：[浮力公开课备课________]   │
│                                     │
│  选择Agent团队（预设模板）：          │
│  ○ 备课全流程 (教学设计+课件+习题)    │
│  ○ 考试分析 (学情分析+教学调整)      │
│  ○ 自定义Agent组合                  │
│                                     │
│  知识库：[初中物理_┘] (已关联)       │
│                                     │
│  [取消]  [创建会话]                  │
└─────────────────────────────────────┘
```

**聊天界面（领域增强）**：
```
┌─────────────────────────────────────────────┐
│ 📚 教学空间 / 浮力公开课备课                  │
│ ─────────────────────────────────────────── │
│                                             │
│  [用户] 我要准备一堂初中物理"浮力"的公开课    │
│                                             │
│  [AI-教学设计师]                             │
│  ┌─ 任务计划 ─────────────────────────────┐ │
│  │ 📋 教学设计 (课程设计Agent)             │ │
│  │    设计教学目标、重难点、教学活动         │ │
│  │ 🎨 课件制作 (课件制作Agent)    [并行]   │ │
│  │    制作互动教学PPT                      │ │
│  │ ✏️ 习题生成 (习题生成Agent)    [并行]   │ │
│  │    设计课堂练习与课后作业                │ │
│  │ ✅ 审核汇总 (教学设计师)                │ │
│  └────────────────────────────────────────┘ │
│                                             │
│  [Agent-课程设计助手] 🔄 执行中...           │
│  ████████░░░░ 80%                           │
│  ✓ 教学目标已设计                            │
│  ✓ 教学活动已规划                            │
│  → 正在编写教案详细步骤...                    │
│                                             │
│  [Agent-课件制作助手]                        │
│  📄 浮力公开课.pptx                   [预览] │
│  🌐 阿基米德实验互动模拟.html          [预览] │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 8. 实施计划

### 8.1 总体时间线（8周，可根据比赛截止日期调整）

```
Week 1-2: 领域架构基础
Week 3-4: 领域能力包系统
Week 5-6: 领域知识库(RAG)
Week 7  : 前端改造与联调
Week 8  : 测试、文档、演示准备
```

### 8.2 详细任务分解

#### 第一阶段：领域架构基础（Week 1-2）

| 任务 | 文件/模块 | 说明 |
|---|---|---|
| 1.1 数据库扩展 | `sql/migration_v2.sql` | 新增workspaces、domain_capability_packages、knowledge_bases表；conversations新增workspace_id字段 |
| 1.2 Workspace模型 | `backend/app/models/workspace.py` | SQLAlchemy模型 |
| 1.3 Workspace仓储 | `backend/app/repositories/workspace_repo.py` | 数据访问层 |
| 1.4 Workspace服务 | `backend/app/services/workspace_service.py` | 业务逻辑：创建、配置、切换、归档 |
| 1.5 Workspace控制器 | `backend/app/controllers/workspace_controller.py` | REST API |
| 1.6 领域种子数据 | `backend/app/services/domain_service.py` | 三个领域的Agent模板预设 |

#### 第二阶段：领域能力包系统（Week 3-4）

| 任务 | 文件/模块 | 说明 |
|---|---|---|
| 2.1 能力包模型 | `backend/app/models/domain_package.py` | 能力包数据模型 |
| 2.2 能力包管理器 | `backend/app/services/package_manager.py` | 包的导入、解析、验证、安装 |
| 2.3 能力投影适配 | `backend/app/sandbox/container/capabilities.py` (修改) | 支持领域级能力包投影到容器 |
| 2.4 办公领域包定义 | `packages/office/v1/manifest.json` | 办公Agent+工具+工作流定义 |
| 2.5 教学领域包定义 | `packages/teaching/v1/manifest.json` | 教学Agent+工具+工作流定义 |
| 2.6 学习领域包定义 | `packages/learning/v1/manifest.json` | 学习Agent+工具+工作流定义 |
| 2.7 工作流模板引擎 | `backend/app/services/workflow_template_service.py` | 预设工作流的自动展开→Moderator计划 |

#### 第三阶段：领域知识库/RAG（Week 5-6）

| 任务 | 文件/模块 | 说明 |
|---|---|---|
| 3.1 Milvus集成 | `backend/app/services/vector_store.py` | Milvus连接、集合管理 |
| 3.2 文档摄入管道 | `backend/app/services/document_ingest.py` | 文档上传→分块→Embedding→入库 |
| 3.3 知识检索服务 | `backend/app/services/knowledge_retrieval.py` | 语义检索+Rerank |
| 3.4 容器内RAG工具 | `backend/app/sandbox/container/tools/rag_tool.py` | 让容器内Agent调用知识检索 |
| 3.5 办公知识库初始化 | 脚本 | 公文规范、模板库初始数据导入 |
| 3.6 教学知识库初始化 | 脚本 | 课程标准、教学设计方法论文档导入 |
| 3.7 学习知识库初始化 | 脚本 | 学科知识图谱、题库导入 |

#### 第四阶段：前端改造（Week 7）

| 任务 | 文件/模块 | 说明 |
|---|---|---|
| 4.1 Workspace Store | `frontend/src/store/modules/workspace.js` | Vuex工作空间状态管理 |
| 4.2 Workspace API | `frontend/src/api/workspace.js` | 前端API调用封装 |
| 4.3 Workspace列表页 | `frontend/src/views/WorkspaceList.vue` | 工作空间管理和切换 |
| 4.4 领域仪表盘 | `frontend/src/views/WorkspaceDetail.vue` | 领域特定首页 |
| 4.5 侧边栏改造 | `frontend/src/components/Sidebar/index.vue` (修改) | 新增Workspace选择器 |
| 4.6 会话创建改造 | `frontend/src/components/ChatWindow/index.vue` (修改) | 领域Agent模板选择 |
| 4.7 领域能力包市场 | `frontend/src/views/DomainMarketplace.vue` | 能力包浏览和安装 |

#### 第五阶段：测试与交付（Week 8）

| 任务 | 说明 |
|---|---|
| 5.1 后端集成测试 | Workspace CRUD、能力包安装、RAG检索、跨域数据桥 |
| 5.2 前端功能验证 | 空间切换、会话创建、Agent协作、产物预览 |
| 5.3 端到端场景测试 | 三个领域各走一遍完整用户旅程 |
| 5.4 演示材料准备 | Demo视频脚本、演示数据、PPT |
| 5.5 文档完善 | 技术文档、使用手册、参赛材料 |

---

## 9. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| **RAG知识库质量不足** | 中 | 高 | 第一版使用高质量精选文档（100-500篇/领域），优先保证精度而非覆盖率；后续迭代扩展 |
| **Milvus部署复杂度** | 中 | 中 | 备选方案：使用轻量级ChromaDB作为向量存储，降低部署门槛；同时提供Docker Compose一键部署 |
| **领域工具开发耗时** | 中 | 中 | 优先复用现有能力系统中的通用工具（文件读写、代码执行、网页生成），领域专用工具采用Python脚本+Function Calling方式快速实现，不追求完美 |
| **跨域数据桥复杂化** | 低 | 中 | 第一版简化为"分享链接"模式：教师生成作业链接→学生通过链接加入→在各自Workspace独立完成→结果汇总到教师端。避免构建复杂的实时跨域系统 |
| **评委理解成本高** | 中 | 高 | 制作3个场景的演示视频（各2-3分钟），准备简明的架构图，现场提供可操作Demo |
| **比赛时间紧张** | 中 | 高 | 采用MVP策略：第一版每个领域2-3个Worker Agent + 1个核心工作流；展示完整的"切换领域→创建会话→多Agent协作→产物交付"链路即可 |

---

## 10. 预期成果与展示方案

### 10.1 预期成果

| 成果类型 | 具体内容 |
|---|---|
| **可运行系统** | 支持三大领域隔离、各含3-4个专属Agent、1-2个工作流模板、基础知识库的完整平台 |
| **技术文档** | 架构设计文档、API文档、部署文档、领域能力包开发指南 |
| **演示视频** | 3个场景演示视频（行政办公、教学备课、个性化学习） |
| **演示数据** | 3个领域预置的Agent团队、知识库内容、示例工作流 |
| **PPT** | 参赛展示PPT（项目背景、技术创新、产品演示、应用价值） |

### 10.2 核心演示脚本

**演示主线**（8分钟）：

1. **开场（1分钟）**：展示领域空间切换——办公→教学→学习，强调同一平台三种专业体验
2. **场景一-行政办公（2分钟）**：从会议录音→纪要→通知→报表的全流程
3. **场景二-教学（2分钟）**：教师备课全流程，展示课件在线预览
4. **场景三-学习（2分钟）**：学生个性化学习路径，展示练习教练的实时反馈
5. **架构展示（1分钟）**：架构图讲解——领域隔离+多Agent协作+沙箱执行

### 10.3 展示亮点（加分项）

1. **实时性**：Agent执行过程实时流式展示，不是录屏
2. **可交互**：评委可以实际创建会话，体验Agent协作
3. **多端展示**：Web端演示，Desktop和Android端作为补充展示
4. **故障演示**：展示Agent异常时的自动重试和容错

---

## 附录A：与大赛其他赛题的结合可能性

| 赛题方向 | 结合可能 |
|---|---|
| **智慧教育** | 教学+学习双空间天然契合智慧教育场景 |
| **智慧城市** | 行政办公空间可扩展到政务办公场景 |
| **数字文旅** | 新增"文旅导览"领域空间（导游Agent+翻译Agent+行程规划Agent） |
| **司法智能服务** | 新增"司法辅助"领域空间（法规检索Agent+文书撰写Agent+案例分析Agent） |

这种可扩展性本身就是项目竞争力的体现——底层架构支持快速孵化新领域方案。

---

## 附录B：与现有产品/竞品的差异化

| 对比维度 | Coze/Dify | MetaGPT/AutoGPT | ChatGPT Projects | WeAgent Domain |
|---|---|---|---|---|
| Agent协作 | 工作流编排 | 多Agent对话 | 单Agent | **主持+Worker双层调度** |
| 领域隔离 | 知识库隔离 | 无 | 无 | **完整领域空间隔离** |
| 执行环境 | 云端函数 | 本地进程 | 云端 | **Docker沙箱完全隔离** |
| 产物类型 | 文本为主 | 代码+文本 | 文本+图片 | **代码/网页/文档/表格/PPT/服务预览** |
| 客户端 | Web | CLI | Web/App | **Web+Desktop+Android** |
| 领域深度 | 知识库RAG | 通用 | 通用 | **领域Agent团队+知识库+工具+工作流** |
| 教学闭环 | 无 | 无 | 无 | **教学↔学习双循环** |

---

> **总结**：本项目以**经过工程验证的多Agent协作平台为基础**，向上构建**领域隔离的Agent工作空间**，通过**可插拔的领域能力包**和**教学-学习双循环生态**，在技术创新和场景应用两个维度均具备显著竞争力。项目可行性高、差异化强、展示效果好，是赛题一的优质参赛方案。
