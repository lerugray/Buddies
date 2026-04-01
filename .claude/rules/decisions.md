# Architecture Decisions

- **Python + Textual** — easiest for non-programmer to maintain with Claude's help
- **httpx (raw HTTP)** for AI backend — no heavy litellm dependency
- **Deterministic gacha** — same user seed always gets same species
- **SQLite via aiosqlite** — async local storage, no server needed
- **Event-driven hooks** — hooks write JSONL, observer polls, TUI updates
- **Zero Claude token cost** — everything runs locally except MCP tools (tiny payloads)
- **HANDOFF.md for shared state** — travels via git between machines
- **CLAUDE.md is local/gitignored** — each machine gets its own with machine-specific notes
- **Prose engine is rule-based** — no AI dependency for personality, works offline
- **Half-block pixel art** — Unicode ▀▄█ characters, colored with Rich markup
