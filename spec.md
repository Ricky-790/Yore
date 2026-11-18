# Ledger v2: a memory layer you own

A self-hostable, time-aware memory service that plugs into any personal AI assistant (Hermes, Grok Bot style, Claude Code, and others).

## 1. Problem

Personal assistants forget you between sessions, or remember you inside someone else’s cloud. Today’s memory layers have four gaps:

1. **Cold start.** A new assistant knows nothing about you until you have chatted with it for weeks.
2. **Stale memory.** Old facts (“works at X”, “lives in Y”) keep being served as true, and almost nobody tests for it.
3. **No real control.** You can’t easily see, limit, or delete what is remembered, and every agent can see everything.
4. **Weak plug-in story and weak safety.** Many layers only work as MCP tools the model has to remember to call. Text from strangers (an incoming email) can also sneak in as an “instruction”.

## 2. Solution overview

Ledger v2 is one memory service the user owns. It does four things:

1. **Bootstraps** from connected sources, so it is useful on day one.
2. **Filters** every memory through a policy-aware chain before anything is saved.
3. **Stores** time-aware facts that always point back to where they came from.
4. **Plugs in** to agents through automatic hooks or through MCP and SDKs, with a console where the user can see and control everything.

## 3. Features

### 3.1 Bootstrap from connectors

- Google (Gmail, Calendar, Drive, Contacts) through OAuth.
- WhatsApp and Discord through their data exports (no unofficial bridges).
- PDFs, .md and .txt files, and chat transcripts through upload.
- A bounded first backfill (for example, the last 6 to 12 months, sent mail first), then incremental sync.
- Two extraction passes. A cheap pass with no LLM counts who you talk to and how often (the people graph). An LLM pass pulls out facts, preferences, writing style, and open commitments.

### 3.2 Filter chain (every memory goes through it)

Pre-filter → extract → redact → classify → scope-route → reconcile → save.

- Each stage is a swappable component with a defined interface.
- Redaction runs before anything is saved, so blocked topics never reach storage or history.
- Reconcile compares with similar memories and decides: supersede, merge, or skip.

### 3.3 Memory model

- A fact has: subject, predicate, object, source pointer, trust, confidence, `observed_at`, `valid_to`, `supersedes`, scope.
- Each category has a **volatility class** (identity is permanent, employer lasts months, location days, mood hours). It drives decay and staleness.
- Raw text is not kept after extraction. Only a pointer to the original (such as a Gmail message ID) is stored.

### 3.4 Read path

- Scope check → hybrid search (full-text plus vectors) → rank by relevance, recency, and volatility → token budget.
- Every result carries a **staleness score** and a `verify_before_use` flag.
- A short always-on profile is returned at session start.

### 3.5 Privacy and control

- User rules, such as “never remember health topics” or per-category retention.
- Per-agent scopes: a named scope is granted to an agent (the coding agent can’t read the email scope).
- Source trust levels. Content from untrusted sources is quarantined and can never be returned as an instruction.
- Deletion leaves a tombstone that holds only a hash (no content), then marks the profile for rebuild.

### 3.6 Adapters

- **Hook adapter** for harnesses with lifecycle hooks (Hermes memory provider, Claude Code hooks): recall before the turn, capture after the turn, flush at session end.
- **MCP server** for harnesses without hooks.
- Python and TypeScript SDKs.

### 3.7 Console

“Show me what you remember”, edit and delete memories, edit rules and scopes, connector status.

### 3.8 Self-monitoring and deployment

- tHealth endpoints and metrics: extraction counts, redaction rate, recall latency, stale-hit rate.
- A small eval set (recall, freshness, deletion) that runs on its own.
- Migrations, config, and Docker. Postgres with pgvector, or SQLite in a single file.

## 4. Unique points

1. **User-owned, policy at write time.** Sensitive content is redacted before it is saved, not hidden later.
2. **Useful on day one.** Bootstrap from the sources you already use.
3. **Knows when it might be wrong.** Staleness score and `verify_before_use` on every recall.
4. **Safe with outside text.** Trust tags and quarantine stop injected instructions.
5. **Real erasure with history.** Hash-only tombstones and profile rebuild.
6. **Per-agent scopes.** Different agents see different memory.
7. **Hooks and MCP.** Dependable automatic recall and capture where hooks exist, with MCP as the fallback.
8. **Monitors itself.** Health, metrics, and eval are built in.

## 5. Tech stack (default)

Python and FastAPI core, Postgres with pgvector (or SQLite with sqlite-vec), background workers for sync and consolidation, MCP server, and a thin TypeScript SDK. One user per instance.

## 6. Out of scope for v1

Full bitemporal modeling, multi-user tenancy, graph traversal in search, a public competitor benchmark suite, and an encrypted cloud backend (the storage interface allows it later).

## 7. Build order

1. Core schema and filter chain, with transcript and PDF import.
2. Recall, profile, and the Hermes hook adapter.
3. MCP server and SDKs.
4. Gmail connector.
5. Console and rules editor.
6. Calendar, Drive, WhatsApp and Discord exports.
7. Metrics and eval.
