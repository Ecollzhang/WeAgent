# Education Durable Domains Implementation Plan

> Date: 2026-07-29  
> Branch: `feature/education`  
> Design source: `docs/education-specs/2026-07-29-durable-workspaces-and-agent-tools-design.md`

## Delivery contract

This plan extends the existing teacher–student MVP without coupling durable
course data to a chat, an Agent run, or a Docker sandbox.

The phase is complete only when all of the following are true:

- uploaded and adopted files remain available from the Education database after
  their source sandbox or local upload directory is removed;
- the teacher domain rail exposes **教学空间**, **PPT 与课件**, and
  **学生画像与评估** as independent course-driven product domains rather than
  Agent workbench tabs;
- the student domain rail exposes **模拟考试**, **作业弱点**, and
  **课程思维导图**;
- **PPT 与课件** selects a course and lesson, consumes an explicit lesson
  context projection, and manages editable SlideDocument versions and
  HTML/PPTX/PDF exports;
- **学生画像与评估** combines finalized assignments and submitted mock exams,
  showing class highest/lowest/average/median, completion, distribution, trend,
  filters, and evidence drill-down without mixing unconfirmed AI scores into
  official data;
- each course has a working Question Bank, Paper Bank, and Knowledge Base;
- UI and Agent tools call the same Education application services;
- Agent writes are membership-scoped, capability-scoped, idempotent, and
  audited;
- automated tests, production builds, browser UAT, and real Agent UAT pass;
- no P0/P1 issue remains and no secret is committed.

## Current-baseline execution update

The repository already has independent routes for the three teacher entries,
course and lesson selection in the courseware page, durable Education assets,
multi-format export adapters, and per-student mock-exam evidence. The remaining
work must therefore extend these product seams instead of replacing them with a
new collaboration console.

### R1 — Domain contract and navigation

- rename the normal Education surface from “教学协作台/教师工作台” to an
  Education domain rail;
- keep the three teacher routes independent and membership-driven;
- make Agent run details secondary and collapsible;
- add frontend contract tests for labels, routes, mixed-role courses, and the
  absence of runtime IDs.

### R2 — Courseware lesson-context projection

- add one read model/API that resolves the selected course and lesson into
  lesson-plan version, objectives, activities, authorized materials, Knowledge
  Base sources, and existing SlideDocument versions;
- use that projection as the only input seam for manual and Agent generation;
- complete editable slide-page operations, immutable version save, HTML
  preview, and PPTX/PDF/HTML export fallback;
- verify the domain works without opening a conversation.

### R3 — Official grade and class-insight projection

- combine finalized assignment submissions with submitted mock-exam attempts;
- exclude unconfirmed AI suggestions and unreviewed subjective work;
- use raw score/max score for one assessment and normalized percentages for
  cross-assessment course aggregates;
- calculate highest, lowest, average, graded count, completion rate, and score
  distribution;
- retain source IDs so every statistic and student recommendation can drill
  down to evidence.

### R4 — Teacher analytics experience

- add class overview cards, assessment/time/learning-domain filters, and score
  distribution and trend;
- retain per-student cards, but add grade trend, assignment completion, rubric
  dimensions, knowledge points, and evidence drawer;
- show explicit “数据不足/待教师确认” states instead of filling missing values
  with Agent guesses.

### R5 — Embedded Agent and release verification

- let courseware and insight Agents call the same R2/R3 application services
  through scoped Education tools;
- keep status, tool results, adopted versions, provenance, fallback, and retry
  visible in collapsed records;
- run backend/frontend regression, production build, teacher/student browser
  UAT, real Agent UAT, and sandbox-deletion persistence recovery;
- update UAT evidence, commit verified slices atomically, then push
  `feature/education` at the final release gate.

### R6 — Refined domain UI and help

- preserve the existing green paper/editorial language with restrained page,
  metric, chart, and version transitions;
- respect reduced-motion preferences and keep mobile interactions direct;
- add a lightweight illustrated Help Center for teacher and student quick-start
  flows after the real pages are stable;
- verify every help route, label, screenshot/diagram, and role boundary in UAT.

## Slice A — Durable assets

### A1. Failing contract tests

Add HTTP tests for:

- database-backed multipart upload and byte-for-byte download;
- teacher/student/private visibility enforcement;
- cross-course and non-member denial;
- checksum metadata;
- legacy `EducationMaterial.storage_path` adoption;
- download after the original filesystem path is deleted.

### A2. Domain and application service

Implement:

- `EducationAsset` as the authoritative binary record;
- a storage-neutral asset service whose first provider is database BLOB;
- course membership and visibility checks in the service, not only routes;
- transaction-safe upload, download, archive, and legacy adoption;
- nullable `EducationMaterial.asset_id` while retaining legacy path reads.

### A3. Product API

Expose:

- `POST /api/edu/courses/{course_id}/assets`;
- `GET /api/edu/courses/{course_id}/assets`;
- `GET /api/edu/assets/{asset_id}`;
- `GET /api/edu/assets/{asset_id}/download`;
- `POST /api/edu/materials/{material_id}/adopt`.

Commit after the focused backend suite passes.

## Slice B — Course Knowledge Center

### B1. Failing contract tests

Cover:

- immutable question and answer versions;
- canonical choice schema (`options` contain plain text only);
- teacher-private answers;
- paper versions freezing ordered item-version references;
- published-only resources for students;
- knowledge-resource ingestion lifecycle and file availability during RAG
  failure.

### B2. Models and services

Implement:

- Question Bank identities, item versions, answer versions, and lifecycle;
- Paper Bank identities and immutable versions;
- Knowledge Base resources linked to durable assets;
- deterministic paper composition by scope, difficulty, and count;
- course context aggregation for UI and Agents.

### B3. Product API

Expose course-scoped endpoints for:

- question list/create/version/publish/archive;
- paper list/compose/version/publish;
- knowledge-resource list/create/ingestion status;
- a consolidated Knowledge Center summary.

Commit after model, authorization, and HTTP tests pass.

## Slice C — Student evidence loop and teacher insight

### C1. Failing contract tests

Cover:

- mock exam generation from published question versions;
- attempt save/submit and objective scoring;
- immutable attempt-to-paper references;
- weakness output containing evidence, not unsupported labels;
- mind-map version creation from published course sources;
- teacher insight refresh from assignments and mock attempts.
- official class aggregates using rule-scored objective work and
  teacher-confirmed subjective `final_score` only;
- highest, lowest, average, median, graded count, completion rate, score
  distribution, and trend for course and selected assessment scopes;
- unconfirmed AI suggestions remaining visible as pending evidence but excluded
  from official statistics;
- mixed assignment/mock-exam evidence, no-evidence students, and partially
  graded classes.

### C2. Services and API

Implement:

- mock exam attempts, answer snapshots, score, and learning events;
- evidence-backed weakness projections;
- versioned editable mind-map JSON with source links;
- a class insight query/projection over finalized assignment grades and
  submitted mock-exam results;
- per-student and class insight snapshots with source references;
- assessment, time-range, learning-domain, and knowledge-point filters;
- explicit “数据不足” states.

Commit after the complete teacher–student API loop passes.

## Slice D — Role-aware Education product domains

### D1. Frontend contract tests

Add tests for:

- active-course role resolution without a fake global role switch;
- exact teacher/student rail labels;
- absence of “教学协作台” and Agent-workbench terminology in normal domain
  navigation;
- mixed-role course selection;
- persisted empty/loading/error/success states;
- upload/download and knowledge-center actions.
- courseware context loading by selected course and lesson;
- class score cards and evidence drill-down using official-grade semantics;
- Agent panels remaining secondary/collapsible while normal domain operations
  work without a chat.

### D2. Shared shell

Implement:

- an Education module rail inside the existing global shell;
- a role-labelled active-course selector;
- route guards driven by server membership;
- responsive narrow-screen behavior.
- domain labels and descriptions centered on course operations rather than
  Agent collaboration.

### D3. Teacher pages

Implement:

- **教学空间** using the existing course and lesson flow;
- **PPT 与课件** with course → lesson selection, a lesson-context summary,
  editable SlideDocument source, HTML preview, immutable version history,
  upload, download, page regeneration, and PPTX/PDF/HTML export;
- **学生画像与评估** with class highest/lowest/average, graded count,
  median, completion rate, distribution, trend, assessment/time filters,
  student cards, and evidence drill-down;
- course Knowledge Center tabs for questions, papers, and resources.

Agent generation and analysis actions stay inside these pages. Their progress
and provenance are shown in a collapsed record area; they do not turn either
page into a generic collaboration console.

### D4. Student pages

Implement:

- **模拟考试** creation, completion, submission, and result;
- **作业弱点** evidence and recommended follow-up practice;
- **课程思维导图** generation, editing, versioning, and source navigation.

Add a shared Help Center entry with role-aware illustrated teacher and student
quick-start guides. Apply purposeful domain-page motion and explicit
`prefers-reduced-motion` fallbacks without introducing a second design system.

Commit after frontend tests and production build pass.

## Slice E — Education Agent Tool Gateway

### E1. Failing security and behavior tests

Cover:

- trusted actor and course scope cannot be widened by model arguments;
- teacher/student capability separation;
- expired or mismatched run grant denial;
- write idempotency;
- sanitized audit records;
- partial and atomic roster imports;
- one teacher and one student tool completing real business writes.

### E2. Shared commands

Refactor UI-facing mutations into application commands used by both HTTP
controllers and tools. Initial tools:

- `edu.course.create`, `edu.course.members.import`, `edu.lesson.create`;
- `edu.asset.attach`, `edu.question_bank.upsert`, `edu.paper.compose`;
- `edu.courseware.create`, `edu.student_insight.refresh`;
- `edu.mock_exam.create`, `edu.weakness.analyze`, `edu.mind_map.create`;
- read-only course, member, context, question, and knowledge queries.

### E3. Gateway and core adapter

Implement:

- tool catalog and schema endpoint;
- short-lived run grants;
- invocation endpoint with idempotency and audit;
- `EducationRuntimeClient` adapter in core;
- Agent-facing tool results that point to durable Education objects, never
  arbitrary host paths.

Commit after security, runtime-client, and regression tests pass.

## Slice F — Migration, UAT, and release

### F1. Existing data

- run idempotent schema upgrades for the local MySQL Education database;
- adopt existing uploaded materials when available;
- preserve all existing course, lesson, assignment, and Agent-run records;
- record non-blocking migration failures in `implementation/ISSUES.md`.

### F2. Verification

Run:

- focused Education backend tests;
- full backend regression suite;
- frontend unit/contract tests and production build;
- direct Education API checks on port 5102;
- proxied UI checks through core and the frontend;
- two-session browser UAT for teacher and student;
- real-model Agent UAT using the ignored root `.env` without printing secrets;
- teacher-domain browser UAT proving course → lesson → SlideDocument →
  multi-version export without entering chat;
- analytics browser/API UAT proving highest/lowest/average from finalized grades
  and exclusion of an unconfirmed AI-suggested score;
- separate teacher and student authorization UAT proving private drafts,
  answers, rubric data, unconfirmed scores, and other students' evidence never
  cross the role boundary;
- Help Center UAT proving screenshots/diagrams, labels, and direct links match
  the current product;
- persistence recovery by removing only a disposable source sandbox/path and
  reopening the adopted asset.

### F3. Version control

- keep one atomic commit per verified slice;
- update `PROGRESS.md`, `ISSUES.md`, and `UAT-REPORT.md`;
- run `git diff --check` and verify `.env` remains ignored;
- push `feature/education` only after the final release gate passes.

## Deferred, explicitly

- creating login accounts from roster PII;
- parent/administrator workbenches;
- cross-course public question sharing;
- IRT/BKT statistical mastery calibration;
- real-time Office co-editing;
- mandatory object storage;
- unrestricted filesystem tools for Agents.
