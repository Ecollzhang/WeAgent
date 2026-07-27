# 数据库表结构附录

本文档给出 AgentHub MVP 的数据库表结构。开发期可使用 SQLite，正式化时迁移到 Postgres。

## users

```sql
create table users (
  id text primary key,
  name text not null,
  created_at text not null
);
```

## conversations

```sql
create table conversations (
  id text primary key,
  title text not null,
  mode text not null,
  owner_id text,
  created_at text not null,
  updated_at text not null,
  archived_at text
);
```

## conversation_agents

```sql
create table conversation_agents (
  conversation_id text not null,
  agent_id text not null,
  primary key (conversation_id, agent_id)
);
```

## messages

```sql
create table messages (
  id text primary key,
  conversation_id text not null,
  run_id text,
  sender_type text not null,
  sender_id text not null,
  content text not null,
  status text not null,
  metadata_json text,
  created_at text not null
);
```

## agent_profiles

```sql
create table agent_profiles (
  id text primary key,
  name text not null,
  provider text not null,
  description text,
  avatar text,
  capabilities_json text,
  system_prompt text,
  tools_json text,
  permissions_json text,
  enabled integer not null default 1,
  created_at text not null
);
```

## runs

```sql
create table runs (
  id text primary key,
  conversation_id text not null,
  user_message_id text not null,
  status text not null,
  orchestrator_plan_json text,
  started_at text,
  completed_at text,
  error text
);
```

## agent_events

```sql
create table agent_events (
  id text primary key,
  run_id text not null,
  agent_id text,
  event_type text not null,
  payload_json text not null,
  created_at text not null
);
```

## artifacts

```sql
create table artifacts (
  id text primary key,
  conversation_id text not null,
  run_id text,
  type text not null,
  title text not null,
  storage_path text,
  preview_url text,
  metadata_json text,
  created_at text not null
);
```

## workspaces

```sql
create table workspaces (
  id text primary key,
  conversation_id text not null,
  path text not null,
  status text not null,
  created_at text not null
);
```

## deployments P1

```sql
create table deployments (
  id text primary key,
  artifact_id text not null,
  status text not null,
  preview_url text,
  logs_json text,
  created_at text not null
);
```

