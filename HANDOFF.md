# BUDDIES — Project Handoff

## What Is This
A tamagotchi-style local AI companion **collection** that runs alongside Claude Code. Your buddies have personality stats (DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE), can be collected, named, customized with hats, and react to your coding sessions.

## Who Am I (The User)
- Game designer / idea person — NOT a programmer
- Claude does all the coding, I design systems and direct
- GitHub: lerugray
- I work across two machines (work computer + home computer)
- Work machine: Intel Iris Xe (integrated graphics, no dedicated GPU)
- Home machine: Unknown GPU — check the `passive-income-hub` project for hardware specs, or just ask me

## Project Status — Phases 1-5 MOSTLY COMPLETE
- **Phase 1** (Foundation): DONE — scaffolding, TUI, buddy character, 25 species with colored half-block pixel art
- **Phase 2** (Session Awareness): DONE — hooks, session observer, pattern detection
- **Phase 3** (Intelligence): DONE — AI backend, query router, rule suggester
- **Phase 4** (MCP Integration): DONE — MCP server with 5 tools, setup scripts
- **Phase 5** (Refactor + Cosmetics): DONE — multi-buddy collection, hats, stat-based unlocking, new species
- **Hatch screen**: Working — named buddies, seed-based or random, name input on hatch
- **Party screen**: NEW — switch between buddies, equip hats, hatch new
- **Hats**: NEW — crown (debug), wizard (wisdom), propeller (chaos), tinyduck (starter)
- **Species**: 25 total (16 original + 9 new: bee, slime, raccoon, parrot, octopus, wolf, robot, tree, void_cat)
- **Animation**: Working — 1-second idle frame cycling per buddy
- **Stats**: DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE (already in code, now more visible)

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

## What Changed (Session 2026-03-31)

### Major Refactor: Single → Multi-Buddy Collection
- **DB Schema**: Removed `CHECK (id = 1)`, added `AUTOINCREMENT`, `is_active`, `hat`, `hats_owned` columns
- **Migrations**: Idempotent SQL migrations for existing databases (backward compatible)
- **BuddyState**: Now includes `buddy_id`, `hat`, and `hats_owned` fields
- **Store methods**: New `get_active_buddy()`, `get_all_buddies()`, `set_active_buddy()`, `update_buddy_by_id()`
- **App wiring**: `create_buddy()` deactivates old buddies instead of deleting; every hatch adds to collection

### New Feature: Hats System
- **4 hat types**: crown (yellow), wizard (blue), propeller (gray+red/blue), tinyduck (yellow)
- **Hat rendering**: Pre-built half-block sprites, prepend to buddy sprite, shiny border applies to hat too
- **Hat unlocking**: Behavior-based on dominant stat at level 5+
  - Crown: high DEBUGGING
  - Wizard: high WISDOM
  - Propeller: high CHAOS
  - Tinyduck: given at hatch (starter hat)
- **Hat display**: Shows in stats ("🎩 crown"), lists owned hats
- **Hat cycling**: In Party screen, cycle through owned hats with [h] key

### New UI: Party Screen
- **File**: `buddy/src/buddy/screens/party.py` (new)
- **Features**: List all buddies with level/rarity, switch active buddy, cycle hats, request new hatch
- **Keybindings**: [enter]=switch, [h]=hat cycle, [+]=hatch new, [escape]=close
- **Navigation**: arrow keys to select buddy, [escape] to close

### HatchScreen Updates
- **Name input**: Added name field; users can customize buddy names on creation
- **Dismiss tuple**: Now 4-tuple: `(Species, bool shiny, str seed, str name)` instead of 3
- **Title**: "🥚 HATCH A NEW BUDDY 🥚" (updated from "HATCH YOUR BUDDY")

### App.py Changes
- **Renamed**: `action_rehatch()` → `action_hatch_new()` (creates, doesn't delete)
- **New keybindings**: [r]=hatch new, [p]=party
- **New methods**: `action_party()`, `_on_party_dismissed()`, `_check_and_unlock_hats()`
- **Updated**: `_update_displays()` (removed StatusBar call), `on_unmount()` (uses `update_buddy_by_id`)
- **Hat unlock check**: Runs after XP gain and stat boosts, notifies user of new hats
- **Title**: Changed to "🐾 BUDDIES"
- **Footer**: Replaced StatusBar with Textual's automatic Footer widget (keybindings shown automatically)
- **Imports**: Removed StatusBar, added Footer, added `check_hat_unlock`, added `json`

### New Species (9 added)
**Common**: bee, slime  
**Uncommon**: raccoon, parrot  
**Rare**: octopus, wolf  
**Epic**: robot  
**Legendary**: tree, void_cat

All 9 have sprite frames (simple pixel art, can be iterated on later)

### Project Rename
- `pyproject.toml`: name="buddies" (was "buddy"), version="0.2.0" (was "0.1.0")
- MCP server title: "Buddies" (was "Buddy")

## Next Steps (Phase 6+)
- [ ] Input box integration — buddy sits beside chat input, reacts to typing
- [ ] Hat cosmetics UI — show owned hats, indicator for locked hats
- [ ] Rename buddies in Party screen (inline Input modal)
- [ ] More animation frames for smoother idle
- [ ] Theme customization (dark/light/custom)
- [ ] Evolution system — buddy appearance changes at level thresholds
- [ ] claw-code integration for agentic local AI
- [ ] Buddy "thoughts" — ambient commentary during sessions
