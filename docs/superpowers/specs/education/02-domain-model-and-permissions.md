# Education 领域模型与权限

## 1. 建模原则

- 业务实体归 Education 服务。
- 核心用户、Conversation、AgentRun、Artifact 只保存字符串 ID 引用。
- 所有可编辑教学内容均版本化。
- 发布内容不可变。
- 草稿和发布版本分离。
- 学生提交保留版本历史。
- AI 建议与教师最终决定分离。
- 可见范围是数据字段和服务端查询条件，不是前端约定。

## 2. 课程结构

### 2.1 Course

关键字段：

- `id`
- `title`
- `subject_code`
- `grade_band`
- `description`
- `owner_user_id`
- `subject_pack_version_id`
- `status`: `draft | active | archived`
- `created_at / updated_at`

课程 owner 必须拥有 active teacher membership。

### 2.2 CourseMembership

- `course_id`
- `user_id`
- `role`: `teacher | student`
- `status`: `invited | active | removed`
- `invited_by`
- `joined_at`
- `removed_at`

唯一约束：`course_id + user_id`。

`workspace.sub_role` 不参与课程授权。

### 2.3 CourseInvitation

- `course_id`
- `token_hash`
- `created_by`
- `expires_at`
- `max_uses`
- `used_count`
- `status`: `active | revoked | expired`
- `created_at`

邀请链接和短码是同一邀请令牌的两种输入形式。服务端只保存 hash；加入课程时必须
校验过期、撤销、使用次数和当前登录用户，成功后幂等创建 CourseMembership。

### 2.4 CourseUnit

Unit 可选：

- `course_id`
- `title`
- `description`
- `position`
- `status`

没有 Unit 的简单课程允许 Lesson 直接归 Course。

### 2.5 Lesson

- `course_id`
- `unit_id`（可空）
- `title`
- `learning_domain`: `reading | writing | integrated`
- `theme_code`
- `text_genre_code`
- `lesson_type_code`
- `duration_minutes`
- `position`
- `status`: `draft | published | archived`
- `current_draft_version_refs`
- `current_published_version_id`

主题、文本类型和课型由 Agent 建议、教师确认。

### 2.6 LessonActivity

- `course_id`
- `lesson_id`
- `activity_type`: `resource | reading | presentation | practice | assignment`
- `title`
- `position`
- `content_version_id`（可空）
- `resource_id / assignment_id`（按类型可空）
- `status`: `draft | published | archived`

Activity 是课时内可排序的学习步骤。发布时冻结为 PublishedLessonVersion 的
`student_release_manifest`，避免学生页面根据变化中的草稿关系临时拼装。

## 3. 版本化内容

### 3.1 EducationContent

统一表示可编辑内容的稳定身份：

- `course_id`
- `lesson_id`（可空）
- `kind`:
  - `lesson_plan`
  - `rich_document`
  - `slide_document`
  - `assessment`
  - `rubric`
  - `teacher_feedback`
  - `student_note`
  - `learning_plan`
  - `knowledge_card`
- `owner_user_id`
- `visibility_scope`
- `current_version_id`
- `status`

### 3.2 EducationContentVersion

- `content_id`
- `schema_name`
- `schema_version`
- `source_json`
- `rendered_html`（可选缓存）
- `parent_version_id`
- `change_summary`
- `created_by_user_id`
- `source_agent_run_id`
- `checksum`
- `created_at`

版本不可覆盖；编辑产生新版本。

结构化真源：

- `rich_document_json`
- `lesson_plan_json`
- `slide_document_json`
- `assessment_json`
- `rubric_json`

## 4. 发布模型

### 4.1 PublishedLessonVersion

- `lesson_id`
- `version_number`
- `lesson_plan_version_id`
- `content_version_ids`
- `assessment_version_ids`
- `activity_ids`
- `student_release_manifest`
- `teacher_evaluation_manifest`
- `artifact_ids`
- `resource_snapshot_ids`
- `subject_pack_version_id`
- `workflow_version_id`
- `published_by`
- `published_at`
- `status`: `active | withdrawn`

同一时刻一个 Lesson 至多有一个 active published version。

`student_release_manifest` 只包含学生可见的活动、题干和 Artifact 引用。
`teacher_evaluation_manifest` 保存答案、解析和 rubric 的版本引用，只能通过教师权限
或服务端判分路径读取。PublishedLessonVersion 的存在不授予调用方读取其全部内部引用。

### 4.2 发布行为

发布前验证：

- 引用的所有版本存在。
- Artifact 生成成功或被教师明确排除。
- 答案和 teacher_private 内容未进入学生包。
- 题目答案与解析通过审校。
- 外部来源具备 URL、抓取时间和引用。
- 教师拥有 course teacher membership。

发布必须使用幂等键，避免重复点击产生两个相同版本。

## 5. 资源模型

### 5.1 LearningResource

- `course_id`
- `owner_user_id`
- `origin`: `upload | web | generated`
- `resource_type`
- `title`
- `visibility_scope`
- `source_url`
- `source_author`
- `published_at`
- `fetched_at`
- `checksum`
- `copyright_status`
- `rag_document_id`
- `artifact_id`
- `status`: `processing | ready | failed | archived`

学生上传资源必须是 `student_private`。

### 5.2 ResourceSnapshot

发布时保存使用的资源版本或 checksum，保证后续网页变化不会悄悄改变历史课时。

## 6. 作业与题目

### 6.1 Assignment

- `course_id`
- `lesson_id`
- `title`
- `kind`: `quiz | writing | mixed`
- `instruction_content_version_id`
- `rubric_version_id`
- `published_lesson_version_id`
- `open_at`
- `due_at`
- `max_attempts`
- `allow_revision_after_feedback`
- `status`: `draft | published | closed | archived`
- `published_by / published_at`

### 6.2 AssessmentItem

题目稳定身份：

- `course_id`
- `subject_code`
- `grade_band`
- `item_type`
- `current_version_id`
- `status`

### 6.3 AssessmentItemVersion

- `item_id`
- `stem_json`
- `material_resource_refs`
- `knowledge_point_codes`
- `difficulty_label`
- `difficulty_source`: `teacher | agent_estimate | statistics`
- `source_refs`
- `created_by`
- `source_agent_run_id`
- `checksum`

MVP 不允许把 `agent_estimate` 显示为“统计校准难度”。

### 6.4 AssessmentAnswerVersion

- `item_version_id`
- `answer_rule_json`
- `explanation_json`
- `created_by`
- `source_agent_run_id`
- `checksum`

答案版本始终为 `teacher_private`，学生端 DTO、Artifact 和 Agent RunGrant 都不得包含
`answer_rule_json`、`explanation_json` 或可解析这些内容的引用。

### 6.5 AssignmentItem

- `assignment_id`
- `item_version_id`
- `answer_version_id`
- `position`
- `points`
- `section`

自动组卷后续通过组卷蓝图创建这组关联。

## 7. Rubric、提交和反馈

### 7.1 Rubric schema

Rubric 使用 `EducationContent(kind=rubric)` 和 `EducationContentVersion` 保存，不建立第二套互相竞争的版本体系。下文的 `rubric_version_id` 均指向对应的 EducationContentVersion。

每个维度包含：

- `criterion_code`
- `title`
- `description`
- `max_score`
- `level_descriptors`
- `subject_pack_source`
- `teacher_overrides`

### 7.2 Submission

- `assignment_id`
- `student_user_id`
- `status`: `draft | submitted | returned | revised | graded`
- `current_version_id`
- `attempt_count`
- `submitted_at`
- `final_score`
- `graded_by`
- `graded_at`

唯一约束：`assignment_id + student_user_id`。

### 7.3 SubmissionVersion

- `submission_id`
- `version_number`
- `answer_json`
- `artifact_ids`
- `submitted_at`
- `source_version_id`
- `checksum`

学生原文不可被 Agent 或规则工具覆盖。

### 7.4 Feedback

`Feedback` 是发布、审核、批注定位和状态流转实体；可编辑的反馈正文保存为
`EducationContent(kind=teacher_feedback)` 的版本，`Feedback` 通过
`content_version_id` 引用对应的 `EducationContentVersion`。这样既保留反馈业务状态，
又不引入第二套正文版本模型。

关键字段：

- `submission_version_id`
- `content_version_id`
- `status`: `draft | approved | released | superseded`
- `approved_by / approved_at`
- `released_by / released_at`

分为：

- `rule_suggestions`
- `agent_suggestions`
- `teacher_feedback`
- `rubric_assessment`

每条建议保存：

- 原文 quote 与上下文。
- 位置 selector。
- 建议内容。
- 规则/Agent/provider。
- `accepted | rejected | modified | pending`。
- 教师修改内容。
- 对学生是否已发布。

教师发布反馈后形成不可变反馈版本。

## 8. 练习与通知

### 8.1 PracticeSession

- `course_id`
- `student_user_id`
- `trigger_type`: `wrong_item | weak_knowledge | teacher_assignment | self_request`
- `knowledge_point_codes`
- `status`: `active | completed | abandoned`
- `created_by_agent_run_id`
- `started_at / completed_at`

### 8.2 PracticeAttempt

- `practice_session_id`
- `item_version_id`
- `answer_json`
- `result_json`
- `error_reason_codes`
- `feedback_version_id`
- `is_variant`
- `answered_at`

PracticeAttempt 产生 LearningEvent，但事件不能代替需要回放的作答事实。

### 8.3 EducationNotification

- `user_id`
- `course_id`
- `type`
- `object_type / object_id`
- `title / body`
- `read_at`
- `created_at`

MVP 只做站内通知；通知失败不影响发布、提交或反馈事实。

## 9. 学科、工作流与 Agent 运行

### 9.1 SubjectPackVersion

- `subject_code`
- `grade_band`
- `version`
- `manifest`
- `knowledge_tree`
- `lesson_plan_template_refs`
- `workflow_template_refs`
- `question_blueprint_refs`
- `rubric_template_refs`
- `capability_version_refs`
- `license_manifest`
- `checksum`

### 9.2 EducationWorkflowDefinition / Version

作用域：

- `system`
- `personal`
- `course`

版本保存当前调度器兼容的节点、边、并行组和教育扩展 metadata。

### 9.3 EducationAgentRun

- `course_id`
- `lesson_id / assignment_id / submission_id`
- `requested_by`
- `workflow_type`
- `workflow_version_id`
- `conversation_id`
- `core_agent_run_ids`
- `status`
- `input_version_ids`
- `output_version_ids`
- `artifact_ids`
- `contributors`
- `approval_status`
- `provider_summary`
- `error_summary`
- `started_at / finished_at`

## 10. 学习事件

LearningEvent 至少支持：

- `LessonPublished`
- `LessonViewed`
- `ResourceOpened`
- `QuestionAnswered`
- `AssignmentSubmitted`
- `SubmissionRevised`
- `FeedbackReleased`
- `FeedbackViewed`
- `SuggestionAccepted`
- `SuggestionRejected`
- `PracticeCompleted`
- `LearningPlanUpdated`

公共字段：

- `course_id`
- `lesson_id`
- `assignment_id`
- `actor_user_id`
- `event_type`
- `object_type / object_id / object_version_id`
- `payload`
- `occurred_at`
- `idempotency_key`

学情分析消费结构化事件，不以聊天记录作为正式统计源。

## 11. 权限矩阵

| 动作 | 教师 | 学生 |
|---|---:|---:|
| 创建课程/课时 | 允许 | 禁止 |
| 邀请成员 | 允许 | 禁止 |
| 查看草稿 | 允许 | 禁止 |
| 查看答案/rubric | 允许 | 禁止 |
| 发布课时/作业 | 允许 | 禁止 |
| 查看已发布内容 | 允许 | 课程成员允许 |
| 查看全班提交 | 允许 | 禁止 |
| 查看本人提交 | 允许 | 允许 |
| 修改本人提交 | 不适用 | 截止/尝试规则允许时 |
| 生成批改建议 | 允许 | 禁止 |
| 确认最终成绩 | 允许 | 禁止 |
| 查看反馈 | 允许 | 仅已发布的本人反馈 |
| 使用 Tutor | 可预览 | 已发布范围内允许 |
| 查询学生私有 RAG | 禁止；只读主动提交的附件快照 | 仅本人 |

## 12. API 与代码层次

Education 服务遵循：

```text
Controller
→ Service
→ Repository/Model
```

- Controller 只解析请求、获取 JWT 身份、调用 Service、返回统一响应。
- Service 执行业务校验、授权、状态机和跨服务调用。
- Model 不包含 HTTP 或 Agent 调度逻辑。
- 对核心服务、RAG 和 Artifact 的调用经过 adapter/client，禁止散落在 Controller。
