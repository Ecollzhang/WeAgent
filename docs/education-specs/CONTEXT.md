# Education

Education is the durable teaching and learning context within WeAgent. It owns
the facts required to operate courses even when no chat, Agent run, or sandbox
still exists.

## Language

**Teaching Space**:
The teacher-facing course workspace containing lessons, members, assignments,
and course assets.
_Avoid_: Chat workspace, sandbox

**Learning Space**:
The student-facing view of published course content, assignments, practice, and
feedback.
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
