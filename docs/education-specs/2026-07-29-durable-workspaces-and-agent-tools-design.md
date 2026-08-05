# Education Durable Domains and Agent Tools

> Status: approved for implementation by delegated product decision  
> Date: 2026-07-29  
> Scope: next product phase after the teacher–student MVP

> Navigation, Agent/chat traceability, sandbox TTL, and courseware quality are
> further refined by
> [Education 单一导航、Agent 双向关联与课件质量设计](./2026-07-29-unified-navigation-agent-chat-and-ppt-quality-design.md).
> The refinements below replace the earlier inner-rail interpretation.

## 1. Outcome

This phase turns the current course MVP into a durable Education product that
continues to work when a chat is deleted, an Agent run expires, or a Docker
sandbox is removed.

The deliverable has four visible outcomes:

1. A role-aware Education product with three independent teacher domains and
   three independent student domains.
2. Course-scoped Question Bank, Paper Bank, and Knowledge Base.
3. Database-owned user files and structured versions; sandbox files are
   temporary only.
4. An Education Tool Gateway that lets Agents perform authorized business use
   cases without coupling Education to the chat UI.

The current high-school English and primary-Chinese reading/writing scope
remains. This phase does not add programming assignments.

## 2. Considered architecture

### Option A — Extend the independent Education service (selected)

Keep one Education application on port 5102, deepen its internal modules, and
expose UI APIs and Agent tool APIs over the same application services.

- Preserves current isolation and course authorization.
- Gives UI and Agents one business behavior instead of parallel implementations.
- Can later be deployed separately without requiring distributed transactions
  now.
- Fits the current repository and medium implementation budget.

### Option B — Merge Education into the core backend

This would simplify local HTTP calls but would mix course permissions, teaching
storage, chat, and sandbox lifecycles. It makes deleting or changing the Agent
runtime risky for normal course operation and is rejected.

### Option C — Split assets, assessment, analytics, and tools into services

This is operationally clean at large scale but introduces service discovery,
distributed consistency, and more deployment dependencies before the product
has that traffic. It is deferred; Option A keeps adapter boundaries that allow
later extraction.

## 3. Ownership and durability

### 3.1 Source-of-truth rule

MySQL `weagent_edu` is authoritative for:

- courses, memberships, lessons, activities, and assignments;
- structured document and assessment versions;
- question and paper versions;
- knowledge-resource metadata and ingestion status;
- student submissions, attempts, learning events, and insight snapshots;
- Agent business runs, tool calls, and adopted output references;
- user-uploaded and adopted generated file bytes.

Core MySQL remains authoritative for users, authentication, conversations,
Agents, capabilities, and core AgentRun facts. Education stores their IDs only.

### 3.2 Education Asset

`EducationAsset` is the durable binary boundary:

```text
EducationAsset
├─ id / course_id / lesson_id?
├─ owner_user_id
├─ purpose
├─ original_filename / media_type / byte_size
├─ sha256
├─ visibility_scope
├─ storage_backend = database
├─ blob_bytes
├─ source_agent_run_id?
├─ source_sandbox_path?
├─ status
└─ created_at / archived_at?
```

The phase stores files up to the configured limit in a database large-binary
column. This is deliberately simple and durable for the current product scale.
The service API remains storage-backend-neutral so an S3/MinIO provider can be
added later without changing course APIs.

Existing `EducationMaterial.storage_path` records are migrated lazily: on first
read or through a migration command, bytes are imported as an Education Asset,
the material is linked to `asset_id`, and the legacy path becomes non-authoritative.

### 3.3 Sandbox boundary

Docker and `/workspace/shared` may contain only run projections and intermediate
outputs. A completed Agent output is not part of a course until Education
validates and adopts it:

```text
durable Education versions/assets
        ↓ least-privilege projection
temporary sandbox collaboration
        ↓ schema validation + explicit adoption
new durable Education version/asset
```

Deleting the conversation, core AgentRun, or container must not delete adopted
course content. Unadopted temporary outputs may be garbage-collected.

## 4. Role-aware product domains

Three information-architecture approaches were considered:

- **Independent course-driven domains (selected):** each left-rail entry owns a
  real product workflow and embeds Agent actions where useful. This matches how
  teachers think about producing courseware and evaluating students.
- **Course-space tabs:** keep courseware and insight inside one large teaching
  space. This reduces routes but makes the two frequent workflows harder to
  enter and mixes authoring with analytics.
- **Agent collaboration console:** organize pages around Agent teams and their
  outputs. This makes orchestration visible but forces teachers to understand
  runtime concepts before completing ordinary work, so it is rejected as the
  primary product structure.

Education uses the existing global WeAgent sidebar as the only domain
navigation. It does not add a second Education rail. A shared current-course
selector lives in the Education page header. Authorization remains
course-specific; there is no fake global teacher/student role switch.

When a user belongs to both teacher and student courses, the active course
determines the module set. The course selector shows the role beside each
course.

The entries in this rail are independent Education product domains, not Agent
workbenches. Each domain owns its own course-driven read model, page flow, APIs,
empty states, and acceptance criteria. Agent collaboration is an embedded
generation or analysis capability behind domain actions. The ordinary teacher
journey must remain usable without opening a chat or understanding Agent
orchestration.

### 4.1 Teacher domains

1. **教学空间**
   - courses, units, lessons, members, activities, assignments;
   - current lesson authoring and publication flow;
   - entry to the course Knowledge Center.
2. **PPT 与课件**
   - enter through a teacher course, then select one lesson;
   - load the lesson plan version, objectives, activities, materials, and
     authorized Knowledge Base sources as the courseware context;
   - use editable slide JSON as the source, with HTML preview and immutable
     version history;
   - treat the selected lesson plan, objectives, activities, materials, and
     publication constraints as a reproducible context snapshot;
   - upload, download, AI-generate, locally edit, regenerate one page, and
     explicitly adopt;
   - PPTX export through an adapter, with HTML fallback.
   - label Agent actions as generation, rewrite, illustration, and validation
     helpers; the default page is not an Agent run timeline.
3. **学生画像与评估**
   - enter through one teacher course and show a class overview before
     per-student cards;
   - aggregate finalized assignment grades and submitted mock-exam results;
   - show highest, lowest, average, graded-student count, completion rate, score
     distribution, median, trend, and assessment/time-range filters;
   - show raw score/max score within one assessment, but normalize scores to a
     percentage before combining assessments with different maximum scores;
   - use submission, score, knowledge-point, error-reason, and rubric evidence
     for per-student insight cards and recommended interventions;
   - include only rule-scored objective work and teacher-confirmed subjective
     grades in official class statistics;
   - display AI-suggested subjective scores as pending evidence and never mix
     them into official highest, lowest, or average values;
   - no personality labels or unsupported mastery probability.

### 4.2 Student domains

1. **教学空间**
   - download and preview published courseware and materials;
   - complete assignments and read released teacher feedback;
   - review assignment-scoped weakness evidence and follow-up practice.
2. **模拟考试**
   - select a course, scope, question count, duration, and difficulty mix;
   - generate from the published Question Bank and optionally validated Agent
     items;
   - persist the paper, attempt, answers, result, and source item versions.
3. **课程思维导图**
   - generate a versioned tree from published course resources and lesson
     objectives;
   - every node can link to a course source;
   - editable JSON is the source, SVG/HTML is a rendering.

Assignment weakness is a tab or aggregate inside student 教学空间, not a
top-level domain. Course lessons and assignments remain reachable within each
domain. Agent run
progress, tool calls, provenance, and generated artifacts may appear in a
collapsed “AI 生成记录” or “分析依据” area, but Conversation IDs, Sandbox IDs,
provider implementation details, and raw reasoning are never primary page
content.

### 4.3 Domain presentation and motion

- Replace product-facing labels such as “教学协作台” and “教师工作台” with
  “Education 教育中心” and “教师领域”/“学习领域”.
- Preserve the existing green, paper, and teaching-material visual language.
  Do not copy a generic analytics dashboard or unrelated design system.
- Use restrained, purposeful motion: one staggered page entrance, animated
  metric changes, chart transitions, and clear hover/focus feedback. All motion
  must respect `prefers-reduced-motion`.
- Durable output, versions, and evidence are visually primary. Agent run details
  stay collapsed under “AI 生成记录” or “分析依据”.

## 5. Course Knowledge Center

Every course has exactly one logical Knowledge Center with three libraries.

### 5.1 Question Bank

- `AssessmentItem` is the stable identity.
- `AssessmentItemVersion` stores the canonical question schema.
- `AssessmentAnswerVersion` is teacher-private.
- Items record source, knowledge points, grade band, difficulty source, and
  lifecycle status.
- Agent-generated items enter as `draft` and require schema validation before
  reuse. Publication of a lesson is still the teacher approval boundary.

### 5.2 Paper Bank

- `AssessmentPaper` is a reusable paper identity.
- `AssessmentPaperVersion` freezes ordered item-version references, sections,
  score, intended duration, and purpose.
- A mock exam creates or references a paper version; a normal assignment may
  also reference one.
- Paper versions never copy or mutate Question Bank answers.

### 5.3 Knowledge Base

- Each stored resource links to an Education Asset or a fetched immutable
  snapshot.
- Ingestion state is `pending | processing | ready | failed | archived`.
- RAG space is `course/{course_id}/teacher` or
  `course/{course_id}/published`.
- Search snippets are candidates only. `ContentFetcher` must obtain body text
  before it can support retrieval or factual Agent output.
- RAG failure does not remove the stored file or block manual course use.

## 6. Independent API and Tool Gateway

### 6.1 API layers

```text
Education UI ───────────────┐
                            ├→ Education Application Services → repositories
Agent Tool Gateway ─────────┘

Core chat/runtime → EducationRuntimeClient → Tool Gateway
```

Public/product APIs remain under `/api/edu/*` on the Education service and are
proxied by core as `/domain/edu/*` for the current same-origin frontend.
The Education service must also be testable and usable directly; it does not
import chat controllers or require an active conversation.

### 6.2 Initial Education tools

Teacher-authorized:

- `edu.course.create`
- `edu.course.members.import`
- `edu.lesson.create`
- `edu.asset.attach`
- `edu.question_bank.upsert`
- `edu.paper.compose`
- `edu.courseware.create`
- `edu.student_insight.refresh`

Student-authorized:

- `edu.mock_exam.create`
- `edu.weakness.analyze`
- `edu.mind_map.create`

Read tools:

- `edu.course.list`
- `edu.course.members.list`
- `edu.course.context.get`
- `edu.question_bank.search`
- `edu.knowledge.search`

`course.members.import` accepts either a validated list of user IDs/usernames or
a durable roster asset. It returns per-row results; one unknown user does not
roll back valid rows unless `atomic=true`.

`asset.attach` accepts an existing core Artifact/file reference or a multipart
Education upload. Agents never receive arbitrary host filesystem paths.

### 6.3 Tool authorization

Every tool call validates:

1. authenticated actor identity;
2. active course membership and required role;
3. immutable input schema and target IDs;
4. capability binding when invoked by an Agent;
5. short-lived Education RunGrant;
6. idempotency key for writes;
7. an `EducationToolCall` audit record with sanitized input and result summary.

The model cannot provide or widen `actor_user_id`, role, course scope, or
visibility. Those values come from the trusted run context.

## 7. Product data flows

### 7.1 Teacher imports a roster through an Agent

```text
teacher uploads/selects roster
→ durable EducationAsset
→ Agent calls edu.course.members.import(asset_id, course_id)
→ service parses and validates rows
→ active/invited memberships created idempotently
→ import report persisted and previewed
```

The initial product supports existing WeAgent usernames. Creating new login
accounts from roster data is out of scope because that needs an explicit
identity-provisioning policy.

### 7.2 Agent creates course content

```text
Agent reads authorized course context
→ creates structured draft in sandbox
→ validator checks canonical schema
→ edu.* write tool adopts it as a durable version
→ UI displays draft and provenance
→ teacher publishes through the existing release gate
```

### 7.3 Student generates a mock exam

```text
published Question Bank + course scope
→ deterministic blueprint filter
→ optional Agent gap-fill into draft items
→ validated paper version
→ student attempt
→ objective scoring / teacher policy
→ LearningEvents
→ weakness evidence and student insight refresh
```

### 7.4 Agent integration contract

Domain services expose stable UI APIs and scoped Agent tools over the same
application-service layer. The tool set may grow and its knowledge-base guide
may be expanded later without changing domain page ownership.

Agents call tools and interfaces; they do not manipulate frontend state, write
Education tables directly, or make sandbox files authoritative. Courseware
tools receive trusted course/lesson scope from the run grant and write validated
draft `SlideDocument` or Education Asset versions. Insight tools read only
authorized final grades and evidence, then persist a reproducible snapshot. The
UI distinguishes deterministic, teacher-confirmed, and AI-suggested values.

## 8. Error handling and recovery

- Database transaction failure leaves no half-created business object.
- Repeated write calls with the same idempotency key return the original result.
- Asset checksum de-duplicates bytes without merging ownership or visibility.
- Invalid Agent schema is rejected and returned to the producing Agent once.
- Courseware runs preflight the actual tool catalog and RunGrant before starting
  a team. Missing `edu.courseware.create` registration fails early.
- Valid courseware without a successful canonical write becomes a recoverable
  draft and retries only the writer once; a second failure remains `partial`.
- Deleted sandbox: adopted assets and versions still open; unadopted output is
  marked unavailable.
- RAG unavailable: Knowledge Base files remain downloadable and are marked
  `ingestion_failed`.
- PPTX adapter unavailable: editable slide JSON and HTML remain usable.
- Analytics with insufficient evidence displays “数据不足”, not a fabricated
  score.
- Partial roster import returns row-level failures and a retryable report.

## 9. Delivery slices

### Slice A — Durable foundation

- EducationAsset database storage and legacy material adoption.
- Course Knowledge Center models and APIs.
- canonical ownership tests and sandbox-deletion recovery test.

### Slice B — Role domains

- one global role-aware domain sidebar and header current-course context.
- teacher and student domain pages with real persisted data.
- empty/loading/error states and responsive behavior.

### Slice C — Assessment and insight

- Question Bank and Paper Bank.
- mock exam creation/attempt.
- evidence-backed weakness and student-insight projections.
- versioned course mind maps.

### Slice D — Agent tools

- Tool Gateway, RunGrant enforcement, idempotency, and audit.
- roster, course, lesson, asset, question, paper, insight, mock exam, weakness,
  and mind-map tools.
- core runtime adapter and visible tool-call results.
- product↔chat deep links, latest-run summary, collaboration history, durable
  visible-artifact snapshots, sandbox TTL, and runtime rehydration.

### Slice E — Product UAT

- teacher creates/imports a course and roster;
- teacher stores knowledge, questions, a paper, and courseware;
- student completes a mock exam and sees evidence-backed weakness analysis;
- student generates and edits a course mind map;
- an Agent performs at least one teacher write and one student write through
  authorized tools;
- adopted files remain downloadable after the originating sandbox is removed.
- teacher UAT verifies course/lesson-driven courseware, editable versions,
  exports, class aggregates, filters, and evidence drill-down;
- student UAT verifies that drafts, private answers, unconfirmed scores, and
  teacher-only evidence never leak across the role boundary;
- a lightweight illustrated Help Center explains both role flows using verified
  screenshots or maintained diagrams.

## 10. Deferred boundaries

- Automatic creation of login accounts from roster PII.
- Parent, teaching-assistant, and administrator education roles.
- statistical difficulty calibration, IRT/BKT, and personality profiling.
- cross-course/global Question Bank sharing.
- real-time collaborative Office editing.
- mandatory S3/MinIO deployment.
- unrestricted Agent access to internal repositories or host files.

These are extension points, not hidden requirements for this phase.
