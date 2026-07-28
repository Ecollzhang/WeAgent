# Education Durable Workspaces Implementation Plan

> Date: 2026-07-29  
> Branch: `feature/education`  
> Design source: `docs/education-specs/2026-07-29-durable-workspaces-and-agent-tools-design.md`

## Delivery contract

This plan extends the existing teacher–student MVP without coupling durable
course data to a chat, an Agent run, or a Docker sandbox.

The phase is complete only when all of the following are true:

- uploaded and adopted files remain available from the Education database after
  their source sandbox or local upload directory is removed;
- the teacher rail exposes **教学空间**, **PPT 与课件**, and
  **学生画像与评估**;
- the student rail exposes **模拟考试**, **作业弱点**, and
  **课程思维导图**;
- each course has a working Question Bank, Paper Bank, and Knowledge Base;
- UI and Agent tools call the same Education application services;
- Agent writes are membership-scoped, capability-scoped, idempotent, and
  audited;
- automated tests, production builds, browser UAT, and real Agent UAT pass;
- no P0/P1 issue remains and no secret is committed.

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

### C2. Services and API

Implement:

- mock exam attempts, answer snapshots, score, and learning events;
- evidence-backed weakness projections;
- versioned editable mind-map JSON with source links;
- per-student and class insight snapshots;
- explicit “数据不足” states.

Commit after the complete teacher–student API loop passes.

## Slice D — Role-aware Education workbench

### D1. Frontend contract tests

Add tests for:

- active-course role resolution without a fake global role switch;
- exact teacher/student rail labels;
- mixed-role course selection;
- persisted empty/loading/error/success states;
- upload/download and knowledge-center actions.

### D2. Shared shell

Implement:

- an Education module rail inside the existing global shell;
- a role-labelled active-course selector;
- route guards driven by server membership;
- responsive narrow-screen behavior.

### D3. Teacher pages

Implement:

- **教学空间** using the existing course and lesson flow;
- **PPT 与课件** with upload, editable source, HTML preview, version history,
  download, and generation/adoption entry points;
- **学生画像与评估** with evidence drill-down;
- course Knowledge Center tabs for questions, papers, and resources.

### D4. Student pages

Implement:

- **模拟考试** creation, completion, submission, and result;
- **作业弱点** evidence and recommended follow-up practice;
- **课程思维导图** generation, editing, versioning, and source navigation.

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

