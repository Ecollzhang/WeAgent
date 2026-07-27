# Education 学科能力包与教案

## 1. 能力包目标

能力包不是一组宽泛 Prompt，而是可版本化的教学设计合同：

```text
SubjectPack
└─ GradeBand
   └─ LearningDomain
      └─ Theme
         └─ TextGenre
            └─ LessonType
               ├─ LessonPlanTemplate
               ├─ WorkflowTemplate
               ├─ QuestionBlueprint
               ├─ RubricTemplate
               ├─ KnowledgePointTree
               └─ AgentPolicy
```

主题、文本类型和课型分别解决：

- **主题**：教什么内容、连接什么背景和价值讨论。
- **文本类型**：采用什么阅读方法、分析什么结构和语言。
- **课型**：课堂按什么步骤推进、如何分配时间和评价。

## 2. SubjectPackVersion

Manifest 至少包含：

- `schema_version`
- `subject_code`
- `grade_band`
- `version`
- `themes`
- `text_genres`
- `lesson_types`
- `knowledge_tree`
- `lesson_plan_templates`
- `workflow_template_refs`
- `question_blueprints`
- `rubric_templates`
- `agent_profiles`
- `capability_version_refs`
- `fallback_policy`
- `license_manifest`

所有运行固定引用 SubjectPackVersion。升级能力包不会改变已发布课时。

## 3. 分类和模板解析

### 3.1 分类输入

- 学科和年级。
- 教材/课文标题。
- 课文正文或教师选中的资料。
- 教师给出的课型、目标和课时长度。
- 当前 Unit 上下文。

### 3.2 Agent 建议

输出：

- `learning_domain`
- `theme_candidates`
- `text_genre_candidates`
- `lesson_type_candidates`
- 每个候选的依据和置信度
- 需要教师回答的不确定项

### 3.3 教师确认

Agent 建议不能直接成为正式元数据。教师可以：

- 选择候选。
- 修改标签。
- 选择“整合课型”。
- 使用通用模板。

### 3.4 Template Resolver

解析键：

```text
subject_pack_version
+ grade_band
+ learning_domain
+ theme_code
+ text_genre_code
+ lesson_type_code
```

fallback 顺序：

1. 精确模板。
2. 同文本类型通用模板。
3. 同 learning domain 通用模板。
4. 学科通用教案模板。

使用 fallback 时必须向教师标记。

## 4. 小学语文能力包

### 4.1 年级分层

#### 低年级

- 识字、写字、拼音。
- 正确朗读。
- 词语和简单句。
- 看图表达和短句写作。

#### 中年级

- 段落理解。
- 复述和概括。
- 观察顺序。
- 片段写作和初步修改。

#### 高年级

- 篇章结构。
- 表达方法。
- 主题和人物理解。
- 完整习作、证据和多轮修改。

### 4.2 主题示例

- 成长与品格。
- 家庭与亲情。
- 自然与生命。
- 传统文化。
- 家国与责任。
- 科学与发现。
- 童话与想象。
- 劳动与生活。

主题树可由教师或学校扩展；统计使用稳定 code，不使用 Agent 自由文本作为主键。

### 4.3 文本类型与侧重点

#### 记叙文

教学重点：

- 事件顺序。
- 人物行为、语言和心理。
- 情感变化。
- 重点句和主题。

活动：

- 时间线。
- 复述。
- 人物卡片。
- 重点句品读。
- 人物或事件仿写。

#### 写景状物

教学重点：

- 观察顺序。
- 感官描写。
- 修辞和关键词。
- 景物与情感关系。

活动：

- 圈画关键词。
- 画面想象。
- 观察表格。
- 片段仿写。

#### 说明文/科普文

教学重点：

- 关键信息。
- 说明对象和特征。
- 分类、顺序、因果。
- 事实和解释。

活动：

- 信息表。
- 结构图。
- 事实判断。
- 用自己的话解释概念。

#### 童话/寓言

教学重点：

- 情节。
- 角色动机。
- 想象。
- 寓意。

活动：

- 角色扮演。
- 情节重排。
- 续写。
- 寓意讨论。

#### 诗歌/儿童诗

教学重点：

- 节奏。
- 意象。
- 情感。
- 朗读和语言积累。

活动：

- 分层朗读。
- 画面联想。
- 诗句仿写。
- 背诵。

#### 古诗/浅易文言

教学重点：

- 字词和停顿。
- 情境。
- 文化背景。
- 适龄理解。

活动：

- 注音释义。
- 节奏朗读。
- 图文还原。
- 关键词解释。

#### 实用类/非连续文本

教学重点：

- 信息目的。
- 格式。
- 图表和文字的关系。
- 实际使用。

活动：

- 通知、说明、图表信息提取。
- 根据要求完成实际表达任务。

#### 习作课

教学重点：

- 观察。
- 选材。
- 结构。
- 具体表达。
- 修改。

活动：

- 写作支架。
- 范例对比。
- 草稿。
- 自评/教师反馈。
- 修订稿。

### 4.4 语文工具

MVP：

- pypinyin。
- 年级字词表。
- 字数、句数、段落、句长、标点、重复词等透明指标。
- PyCorrector 小样本评测通过后作为候选提示。

工具只产生证据和候选，不自动改学生原文。

## 5. 高中英语能力包

### 5.1 主题语境

一级主题：

- 人与自我。
- 人与社会。
- 人与自然。

示例二级主题：

- 成长与学习。
- 健康与生活。
- 社会责任。
- 文化与交流。
- 科学与技术。
- 环境与可持续发展。
- 文学、艺术与体育。

### 5.2 语篇类型与侧重点

#### Narrative

阅读：

- plot
- character
- point of view
- conflict
- emotion/theme

写作迁移：

- story continuation
- character description
- personal narrative

#### Expository

阅读：

- text structure
- facts
- classification
- cause/effect
- comparison

写作迁移：

- summary
- explanation
- structured informational writing

#### Argumentative

阅读：

- claim
- evidence
- reasoning
- counterargument

写作迁移：

- opinion essay
- evidence organization
- rebuttal

#### Practical

阅读：

- purpose
- audience
- format
- register

写作迁移：

- email
- notice
- application
- suggestion letter

#### News/Report

阅读：

- fact/opinion
- source
- headline and lead
- event structure

写作迁移：

- summary
- event report

#### Speech/Interview

阅读：

- speaker stance
- tone
- audience interaction

写作迁移：

- speech
- interview outline

#### Poetry/Drama

阅读：

- imagery
- tone
- rhythm
- character conflict

写作迁移：

- literary response
- role expression

#### Multimodal

阅读：

- relationship among chart, image and text
- data interpretation

写作迁移：

- chart description
- integrated response

### 5.3 英语工具

MVP：

- Harper：确定性 grammar/spelling/style suggestions。
- textstat：阅读材料表层可读性指标。
- 教师维护或能力包提供的词汇/知识点层级。
- Agent：内容、结构、论证和语篇层反馈。

工具命中数不得直接换算为作文最终成绩。

## 6. 课型

MVP 支持：

- 精读/close reading。
- 略读/extended reading。
- 写作课。
- 阅读—写作整合课。
- 复习/练习课。

每个课型定义：

- 默认阶段。
- 时间分配范围。
- 必须活动。
- 可选活动。
- 所需 Agent。
- 题目蓝图。
- 发布检查项。

## 7. 结构化教案

LessonPlan JSON 包含：

### 7.1 基本信息

- 学科、年级。
- 教材版本、Unit、课题。
- 主题、文本类型、课型。
- 课时长度。
- 班级情况和前置基础。

### 7.2 教学依据

- 教师上传的课程要求或课程标准摘录。
- 教材和资料来源。
- 学生已知与可能困难。

### 7.3 教学目标

目标必须有稳定 ID，供活动和评价引用：

- 阅读目标。
- 写作目标。
- 语言/字词目标。
- 学习能力目标。

### 7.4 重点与难点

每项说明：

- 依据。
- 对应目标。
- 解决活动。

### 7.5 活动阶段

每个阶段：

- 名称。
- 时间。
- 教师活动。
- 学生活动。
- 所需资源。
- 目标 IDs。
- 检查/评价方式。
- 分层建议。
- 预计产物。

### 7.6 评价、作业和反思

- 课堂评价。
- 作业设计。
- rubric。
- 板书/页面设计。
- 课后反思（教师填写）。

## 8. 教案生成与派生

```text
教师输入
→ 分类建议
→ 教师确认
→ Template Resolver
→ 资料研究
→ 课程设计 Agent
→ 教学审校
→ 教师编辑
→ LessonPlanVersion
→ 派生讲义、课件和习题
```

教案更新后：

- 不自动覆盖课件和习题。
- 标记下游产物基于的旧版本。
- 提供差异。
- 教师选择局部或完整重新生成。

## 9. 教案质量规则

自动校验：

- 目标是否被活动覆盖。
- 活动是否有评价。
- 时间总和是否合理。
- 阅读输入是否支持写作输出。
- 题目是否覆盖重点知识点。
- 资料是否已获取正文。
- 引用是否可定位。
- 年级和文本类型模板是否匹配。
- 课件、题目和 rubric 是否引用正确教案版本。

## 10. 教案导出

MVP：

- 系统内结构化编辑。
- Tiptap/HTML 阅读视图。
- 通过导出 capability/worker 使用 python-docx 生成可编辑 DOCX。
- PDF 打印。

导出文件写入 Artifact，并记录源 LessonPlanVersion。
导出 worker 可以复用相同的开源依赖，但不得跨服务导入 RAG 解析器的业务实现。
