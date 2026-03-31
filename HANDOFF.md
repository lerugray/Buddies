# Buddy — Project Handoff

## What Is This
A tamagotchi-style local AI companion that runs alongside Claude Code. Inspired by the "Buddy" easter egg found in the Claude Code source leak (March 2026), but designed to be actually useful — not just decorative.

## Who Am I (The User)
- Game designer / idea person — NOT a programmer
- Claude does all the coding, I design systems and direct
- GitHub: lerugray
- I work across two machines (work computer + home computer)
- Work machine: Intel Iris Xe (integrated graphics, no dedicated GPU)
- Home machine: Unknown GPU — check the `passive-income-hub` project for hardware specs, or just ask me

## Project Status — Phases 1-4 COMPLETE, tested & running
- **Phase 1** (Foundation): DONE — scaffolding, TUI, buddy character, 16 species with colored half-block pixel art
- **Phase 2** (Session Awareness): DONE — hooks, session observer, pattern detection
- **Phase 3** (Intelligence): DONE — AI backend, query router, rule suggester
- **Phase 4** (MCP Integration): DONE — MCP server with 5 tools, setup scripts
- **Phase 5** (Polish): NOT STARTED — evolution system, more species, themes
- **Hatch screen**: Working — seed-based, random roll, or reroll. Press `r` in main app to rehatch.
- **Animation**: Working — 1-second idle frame cycling
- **Known issues**: See `session-notes/2026-03-31-session-1.md` for bugs found & fixed

## How To Run

### Launch the TUI
```bash
cd buddy
PYTHONPATH=src python -m buddy
```

### Register hooks (run once)
Adds event hooks so Buddy can watch Claude Code sessions:
```bash
PYTHONPATH=src python -m buddy.setup_hooks
```

### Register MCP server (run once)
Adds Buddy's tools to Claude Code so Claude can interact with buddy:
```bash
PYTHONPATH=src python -m buddy.setup_mcp
```

### Configure local AI backend
Edit `%APPDATA%/buddy/config.json` (or `~/.local/share/buddy/config.json` on Linux):
```json
{
  "ai_backend": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "qwen3.5:27b"
  }
}
```
For remote Ollama (e.g., home machine): change `base_url` to `http://<home-ip>:11434`

## What's Built

### Files
```
buddy/
├── pyproject.toml                    # Project config, dependencies
├── styles/buddy.tcss                 # TUI theme (CSS for Textual)
├── src/buddy/
│   ├── __init__.py
│   ├── __main__.py                   # Entry point
│   ├── app.py                        # Main TUI app — wires everything together
│   ├── config.py                     # Config loading/saving, data dir
│   ├── setup_hooks.py                # Register hooks with Claude Code
│   ├── setup_mcp.py                  # Register MCP server with Claude Code
│   ├── widgets/
│   │   ├── buddy_display.py          # Sprite + stats pane
│   │   ├── chat.py                   # Chat interaction pane
│   │   ├── session_monitor.py        # Live Claude Code activity feed
│   │   └── status_bar.py             # Bottom status bar
│   ├── core/
│   │   ├── buddy_brain.py            # Species, stats, personality, gacha, leveling
│   │   ├── hooks.py                  # Claude Code hook receiver (writes events.jsonl)
│   │   ├── session_observer.py       # Watches events, detects patterns, tracks tokens
│   │   ├── ai_backend.py             # Ollama/OpenAI-compatible API connector
│   │   ├── ai_router.py              # Complexity scoring, local vs Claude routing
│   │   └── rule_suggester.py         # Session pattern → config rule suggestions
│   ├── mcp/
│   │   └── server.py                 # MCP server (5 tools for Claude)
│   ├── art/
│   │   ├── sprites.py                # 16 species, 2 frames each, Unicode art
│   │   └── animations.py             # Frame cycling controller
│   └── db/
│       ├── models.py                 # SQLite schema
│       └── store.py                  # Async data access layer
```

### Key Design Decisions
- **Python + Textual** — easiest for non-programmer to maintain with Claude's help
- **httpx (raw HTTP)** for AI backend — no heavy litellm dependency needed
- **Deterministic gacha** — same user always gets same species (seeded from username)
- **User's species**: Phoenix (Epic) — seeded from "lerugray"
- **Event-driven architecture** — hooks write JSONL, observer polls file, TUI updates
- **Zero Claude token cost** — everything runs locally except the MCP tools (tiny payloads)
- **claw-code integration planned** — for Phase 3+, can use instructkr/claw-code's tool harness to give local model agentic capabilities (read/edit/bash)

### MCP Tools (available to Claude)
1. `buddy_status` — Check buddy's mood, species, stats, level
2. `buddy_note` — Leave a note for the user via buddy's chat
3. `session_stats` — View session event counts and token usage
4. `ask_buddy` — Delegate simple questions to local AI (saves tokens)
5. `get_buddy_notes` — Read unread notes

### Query Router Complexity Scoring
- 0.0 = buddy handles directly (greetings, status, help)
- <0.7 = local AI handles (syntax questions, simple explanations)
- ≥0.7 = suggests asking Claude (refactors, multi-file changes, debugging)

## Dependencies
- `textual>=3.0.0` — TUI framework
- `rich>=14.0.0` — Rich text rendering
- `httpx>=0.28.0` — Async HTTP for AI backends
- `aiosqlite>=0.21.0` — Async SQLite
- `mcp>=1.0.0` — MCP SDK (for server)

## Architecture Decisions

### AI Backend Strategy
Since the work machine has no GPU, the local AI component is flexible:
- Connect to Ollama running on home machine over network
- Use a tiny CPU-friendly model (e.g., Qwen 0.5B or Phi-3 mini)
- Use a free/cheap cloud API
- Graceful fallback: Buddy still works for observation/suggestions without a local model

### Related Projects
- **claw-code** (github.com/instructkr/claw-code) — Clean-room Python reimplementation of Claude Code's tool loop. Could be integrated to give the local model agentic capabilities.
- **DevForge** (lerugray/devforge) — Game dev tool for CC. Buddy could eventually integrate.
- **Qwen3.5-27B** (HuggingFace) — Distilled model for local AI brain (needs RTX 3090+)

## Next Steps (Phase 5 — Polish)
- [ ] Confirm home machine GPU specs and set up Ollama
- [ ] Evolution system — buddy changes appearance at level thresholds
- [ ] More species sprites + animation frames
- [ ] Theme customization (dark/light/custom)
- [ ] Usage dashboard / stats screen
- [ ] claw-code integration for agentic local AI
- [ ] Pick a real name for the project
