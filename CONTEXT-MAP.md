# Context Map

## Contexts

- [Education](./docs/education-specs/CONTEXT.md) — owns courses, teaching assets,
  learning activity, assessment facts, student insight, and the education-facing
  Agent tool contract.
- Core Agent Runtime — owns users, authentication, conversations, Agents,
  capabilities, sandbox execution, and provider integration. Its existing
  architecture documents remain the source of terminology until a dedicated
  context glossary is introduced.

## Relationships

- **Education → Core Agent Runtime**: Education references core users and runs by
  stable IDs and exposes authorized use-case tools. It does not store chat
  messages or execute model providers.
- **Core Agent Runtime → Education**: Agents call Education through the tool
  gateway using a short-lived actor/course grant. They never write Education
  tables or durable files directly.
- **Sandbox → Education**: sandbox files are temporary working projections.
  Adopting an output imports it into an Education version or asset before the
  sandbox may be deleted.
