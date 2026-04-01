# Project Context

Buddies is a tamagotchi-style local AI companion collection that runs alongside Claude Code.

## Current State (v0.2.0+)
- 70 species across 5 rarities (common → legendary)
- 10 hats with behavior-based unlocking
- 4-stage evolution system (Hatchling → Elder)
- Party system: collect, switch, name, equip hats
- Party discussions: buddies debate topics in 3 modes
- Conversation persistence: auto-save, browse, rename, load, delete
- Tool browser: scans .claude/ for MCP servers and skills
- Phase 9: Config intelligence with CLAUDE.md health grading
- AI routing: local model for simple queries, Claude for complex ones
- Session observer: watches CC events, detects patterns, suggests rules

## Two-Machine Setup
- Home: RTX 3050 4GB — can run small Ollama models (3B)
- Work: Intel Iris Xe — CPU-only, use tiny models or skip local AI
- User syncs via git push/pull between machines
- HANDOFF.md is the shared knowledge document
