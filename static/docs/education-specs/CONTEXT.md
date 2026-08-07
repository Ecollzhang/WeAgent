# Education

Education is the durable teaching and learning context within WeAgent. It owns
the facts required to operate courses even when no chat, Agent run, or sandbox
still exists.

## Language

**Teaching Space**:
The role-aware primary Education domain in the global WeAgent Sidebar. Teachers
manage lessons, members, assignments, and course assets; students download
published courseware, complete assignments, and review assignment weaknesses.
It appears exactly once in navigation.
_Avoid_: Chat workspace, sandbox

**Learning Space**:
An internal product term for the student-facing content inside Teaching Space,
not a separate visible navigation layer or sidebar.
_Avoid_: Student sandbox

**Education Asset**:
A durable user-uploaded or adopted generated file whose bytes, checksum,
ownership, and visibility are owned by Education.
_Avoid_: Sandbox file, temporary artifact

**Course Knowledge Center**:
The course-scoped home of the Question Bank, Paper Bank, and Knowledge Base.
_Avoid_: Global knowledge base

**Question Bank**:
Versioned assessment items that may be reused across assignments, mock exams,
and papers within one course.
_Avoid_: Raw Agent exercise file

**Paper Bank**:
Versioned, ordered compositions of Question Bank items with scoring and purpose.
_Avoid_: Assignment

**Knowledge Base**:
Course resources authorized for storage, parsing, and course-scoped RAG.
_Avoid_: Search result snippet, sandbox folder

**Student Insight**:
An evidence-backed summary derived from submissions, attempts, and learning
events, with every claim linked to its source facts.
_Avoid_: Personality score, unsupported mastery probability

**Courseware Domain**:
The independent teacher product area that consumes the course selected in the
shared Education page header, selects a lesson, projects authorized lesson
context into an editable SlideDocument, and manages preview, versions, upload,
publication, and export.
_Avoid_: Agent workbench, chat-based PPT generator

**Student Insight Domain**:
The independent teacher analytics area that combines official finalized grades
with completion and evidence drill-down. AI-suggested subjective scores remain
pending and are excluded from official class aggregates.
_Avoid_: Agent analysis chat, AI-only score dashboard

**Education Tool**:
An authorized Education use case exposed to Agents through the Tool Gateway.
It validates the actor, course role, input schema, and audit record before
calling the same application service used by the UI.
_Avoid_: Database tool, unrestricted internal API

**Adoption**:
The explicit import of a generated Agent output into a durable Education
version or Education Asset.
_Avoid_: Publishing from `/workspace/shared`

**Run Projection**:
A temporary, least-privilege copy of durable Education inputs made available to
one Agent run.
_Avoid_: Source of truth

**Education Collaboration Link**:
The durable association between an EducationAgentRun, its core Conversation,
and the canonical Education object/version produced by a successful tool call.
Product pages show only the latest run and link historical collaboration to
chat; chat links back to the business object.
_Avoid_: Parsing a chat title or sandbox path to find the business object

**Runtime Generation**:
One disposable sandbox instance used to execute or continue a conversation.
Historical messages and user-visible artifacts remain readable after this
instance expires; a later turn may create a new generation and rehydrate
bounded context.
_Avoid_: Permanent conversation container
