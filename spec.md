# Yore: a memory layer you own

Yore builds a user’s memory from their own sources, enforces their privacy rules, and answers recall requests from any agent harness. It does not run agents, skills, or tasks: that stays with the harness.

## 1. Problem

Personal assistants forget you between sessions, or remember you inside someone else’s cloud. Existing memory layers leave four gaps:

1. **Cold start.** A new assistant knows nothing about you until you have talked to it for weeks.
2. **Stale memory.** Old facts (“works at X”) keep being served as true, and almost nobody tests for it.
3. **No real control.** You can’t easily see, limit, or delete what is remembered, and every agent sees everything.
4. **Weak plug-in story and weak safety.** Many layers only work as MCP tools the model has to remember to call, and text from strangers (an incoming email) can be mistaken for instructions.

## 2. What the layer does, and what it leaves to the harness

The layer owns memory data and memory policy. The harness owns everything the agent does with that memory.

| Concern                                                       | Memory layer           | Harness or adapter      |
| ------------------------------------------------------------- | ---------------------- | ----------------------- |
| Agent loop, tool calls, model choice                          | No                     | Harness                 |
| Skills and workflows (such as the steps to reply to an email) | No                     | Harness                 |
| Scheduling, reminders, notifications                          | No                     | Harness                 |
| Taking actions (send mail, fill forms, look up a profile)     | No                     | Harness                 |
| Conversation history and context compaction                   | No                     | Harness                 |
| Agent behavior rules (“ask before sending”)                   | No                     | Harness config          |
| Deciding when to recall or capture                            | Offers both calls      | Adapter                 |
| Writing the query and placing memory in the prompt            | Returns ranked results | Adapter                 |
| Pulling from Gmail and notes                                  | Yes, read-only         | No                      |
| Extracting, consolidating, and storing memory                 | Yes                    | No                      |
| Privacy rules, scopes, deletion                               | Yes                    | No                      |
| Staleness and trust labels                                    | Yes, labels only       | Decides how to use them |

## 3. Solution overview

One memory service the user owns. It bootstraps from connected sources, filters every memory through a policy-aware chain before saving, stores time-aware facts that point back to their source, and answers recall and capture calls from agents through an HTTP API, MCP, or a hook adapter.

## 4. v1 features

### 4.1 Bootstrap

- Input: Gmail (read-only), a notes doc (a plain list of the user’s own points), written instructions, and a time span.
- An LLM compiles the instructions once into structured rules. The user reviews and approves the rules before anything is pulled.
- Code pulls mail for the time span, parses headers and bodies, marks automated mail (noreply senders, bulk headers, Promotions and Updates labels), and builds a people graph from email addresses and message counts. No LLM is involved up to here.
- Automated mail is skipped. Each human thread is read once by an LLM, which proposes memories in a fixed format.
- The notes doc is split into one-line facts by an LLM and saved with the highest trust.
- Raw email text is deleted after extraction, and only a pointer to the original is kept. Notes are kept as written, since they are the user’s own words.

### 4.2 Filter chain

Pre-filter (rules, source trust) → extract → redact → classify → scope-route → reconcile (supersede, merge, or skip) → save. Each stage is a swappable component with a defined interface. Redaction runs before anything is saved.

### 4.3 Memory model

- Every memory has three labels: **kind** (fact, preference, commitment, event, relationship, style), **domain** with an optional subdomain (identity, career, people, communication, schedule, money, health, lifestyle, travel, learning, other), and **predicate** (the specific thing, such as employer or diet).
- A predicate registry (about 25 to start, extendable) sets each predicate’s domain, kind, single or multiple values, and volatility (permanent, years, months, days, hours). Code assigns these, not the LLM.
- Fields: subject, predicate, object, source pointer, trust, confidence, `observed_at`, `valid_to`, `supersedes`, scope, sensitivity flags, status.
- Commitments are stored with a due date but never trigger reminders.

### 4.4 Recall and capture

- **Recall:** scope check → hybrid search (full-text plus vectors) → rank by relevance, recency, and volatility. Each result carries a staleness score, a `verify_before_use` flag, and a trust label. The caller can pass a token limit. A short profile comes from a separate call.
- **Capture:** accepts a turn, a short transcript, or a plain statement. It is queued and processed in the background, and the layer decides what is worth keeping. The layer does not store transcripts.
- The layer returns structured results, plus an optional ready-made text block. Deciding when to call, writing the query, and placing the text in the prompt belong to the adapter.

### 4.5 Privacy and control

- User rules: exclude senders or topics, never remember a domain (for example health), retention by domain.
- Scopes are named groups of domains, and each agent key is granted specific scopes.
- Memories from untrusted sources (automated or unknown senders) are quarantined and left out of recall by default. The layer only labels them: the harness must show memory to the model as data, never as instructions.
- Deleting a memory leaves a tombstone holding only a hash, then marks the profile for rebuild.

### 4.6 Interfaces

The HTTP API is the source of truth. On top of it: a Python SDK, an MCP server, and a first hook adapter for Hermes (recall before the turn, capture after, flush at session end). Adapters stay thin: they translate harness events into recall and capture calls and hold no memory logic.

### 4.7 Console and operations

A minimal console (CLI first): list and search memories, delete, edit rules, see connector status. Health and metrics endpoints (extraction counts, redaction rate, recall latency, stale-hit rate), migrations, config, Docker, and a small automated eval for recall, freshness, and deletion.

## 5. Unique points

1. **User-owned, with policy at write time.** Sensitive content is redacted before it is saved.
2. **Useful on day one.** Bootstrap from the sources people already use.
3. **Knows when it might be wrong.** Staleness score and `verify_before_use` on every result.
4. **Safe with outside text.** Trust labels and quarantine.
5. **Real erasure with history.** Hash-only tombstones and profile rebuild.
6. **Per-agent scopes.** Different agents see different memory.
7. **One core API, several doors.** Hooks, MCP, and SDK share the same service.
8. **Measures itself.** Health, metrics, and a small eval are built in.

## 6. Tech and deployment

Python and FastAPI core. Postgres with pgvector, or SQLite with sqlite-vec for a single-file setup. A background worker handles sync and extraction. The extraction model is a setting (local Ollama or an API model).

v1 runs self-hosted for one user, and each user supplies their own Google OAuth client. Every table carries a `user_id` so a hosted version stays possible later. Going hosted would require Google’s restricted-scope verification and multi-tenant isolation, so it is a separate decision.

## 7. Not in v1

- Skills, workflows, or procedural memory (harness).
- Reminders, notifications, scheduling, and task tracking.
- Drafting or sending email, form filling, and external lookups such as LinkedIn.
- Agent behavior rules such as “never send without asking” (harness config).
- Conversation history or transcript storage.
- Calendar, Drive, WhatsApp, and Discord connectors, and chat-export import.
- Fuzzy entity merging across sources (v1 matches on email address only).
- Graph traversal in search and full bitemporal modeling.
- Multi-tenant hosting and an encrypted cloud backend.
- Custom dashboards, a public benchmark suite, and a TypeScript SDK.

## 8. Build order

1. Schema, predicate registry, filter chain, and the capture and recall API, tested with the notes import.
2. Hermes hook adapter and MCP server.
3. Gmail pull and the bootstrap flow, including rule compilation and approval.
4. Rules, scopes, staleness, quarantine, and tombstones.
5. Minimal console and metrics.
6. Small eval set; then more connectors and hosting.
