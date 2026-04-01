# BUDDIES — Project Handoff

**Folder Status**: ✅ Renamed to `Buddies` (2026-03-31)

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
- **Fun Phase**: DONE — party discussions, tool browser, conversation saving, styled output, 70 species
- **Phase 9** (CC Config Intelligence): DONE — CLAUDE.md health grading, auto-learn rules, config scaffolding
- **Phase 10** (Token Guardian): DONE — rolling summaries, token warnings, quick-save, session handoff
- **Polish**: DONE — 6 themes, 33 achievements, species count audit
- **Hatch screen**: Working — named buddies, seed-based or random, name input on hatch
- **Party screen**: NEW — switch between buddies, equip hats, hatch new
- **Hats**: NEW — crown (debug), wizard (wisdom), propeller (chaos), tinyduck (starter)
- **Species**: 70 total (see buddy_brain.py for full catalog)
- **Animation**: Working — 1-second idle frame cycling per buddy
- **Stats**: DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE (already in code, now more visible)

## How To Run

### Launch the TUI
```bash
cd buddies
python -m buddies
```
Or from anywhere after `pip install -e .` in the buddies folder:
```bash
buddy
```

### Register hooks (run once)
Adds event hooks so Buddy can watch Claude Code sessions:
```bash
python -m buddies.setup_hooks
```

### Register MCP server (run once)
Adds Buddy's tools to Claude Code so Claude can interact with buddy:
```bash
python -m buddies.setup_mcp
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
buddies/
├── pyproject.toml                    # Project config, dependencies
├── styles/buddy.tcss                 # TUI theme (CSS for Textual)
├── src/buddies/
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
│   ├── screens/
│   │   └── party.py                  # Party screen for buddy collection management
│   ├── core/
│   │   ├── buddy_brain.py            # 70 species, stats, personality, gacha, leveling
│   │   ├── prose.py                  # Personality prose engine + discussion templates
│   │   ├── discussion.py             # Multi-buddy discussion orchestrator
│   │   ├── conversation.py           # Chat auto-save/load persistence
│   │   ├── tool_scanner.py           # MCP/skills browser scanner
│   │   ├── agent.py                  # Agentic tool loop (read/grep/bash)
│   │   ├── hooks.py                  # Claude Code hook receiver (writes events.jsonl)
│   │   ├── session_observer.py       # Watches events, detects patterns, tracks tokens
│   │   ├── ai_backend.py             # Ollama/OpenAI-compatible API connector
│   │   ├── ai_router.py              # Complexity scoring, cost guardrails, routing
│   │   ├── rule_suggester.py         # Session pattern → config rule suggestions
│   │   ├── config_intel.py           # CLAUDE.md health, linting, scaffolding, auto-learn
│   │   ├── token_guardian.py         # Rolling summaries, token warnings, session handoff
│   │   ├── achievements.py          # 33 achievements, checking, tracking
│   │   └── model_tracker.py         # Model detection, phase classification, mismatch alerts
│   ├── screens/
│   │   ├── party.py                  # Buddy collection management
│   │   ├── discussion.py             # Party focus group screen
│   │   ├── tool_browser.py           # MCP/skills browser screen
│   │   ├── conversations.py          # Saved conversations browser
│   │   ├── config_health.py          # Config health dashboard screen
│   │   └── achievements.py          # Achievements viewer screen
│   ├── widgets/
│   │   ├── buddy_display.py          # Animated sprite + stats + evolution
│   │   ├── chat.py                   # Chat pane with auto-save
│   │   ├── styling.py                # Centralized Rich markup styles
│   │   └── session_monitor.py        # Activity feed
│   ├── mcp/
│   │   └── server.py                 # MCP server (5 tools for Claude)
│   ├── art/
│   │   ├── sprites.py                # 70 species, 10 hats (half-block pixel art)
│   │   └── animations.py             # Frame cycling controller
│   ├── db/
│   │   ├── models.py                 # SQLite schema
│   │   └── store.py                  # Async data access layer
│   └── first_run.py                  # Hatch screen for initial buddy creation
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

## Completed Phases

### Phase 6: Buddy Thoughts & Personality Prose — DONE
- ✅ Prose engine with 5 registers, ~80 templates, compositional closers
- ✅ Context-aware animation (excited/normal/sleepy speeds)
- ✅ 4-frame animations for 7 species (expressions, idle behaviors)
- ✅ Mood-reactive gameplay (XP multipliers, bonus stats, hat discovery)

### Phase 7: Polish & QoL — DONE
- ✅ 10 new species (35 total), 6 new hats (10 total)
- ✅ Evolution system (Hatchling → Juvenile → Adult → Elder) with visual borders
- ✅ Party screen polish, inline rename with [n], evolution stage display
- ✅ Mood decay system (drifts toward neutral, neglect has consequences)
- ✅ One-click setup.bat/launch.bat for non-programmers

### Phase 8: Agentic Local AI — DONE
- ✅ Agent loop with tool calling (read_file, list_files, grep_search, run_command)
- ✅ Safety: path traversal blocked, destructive commands blocked, output truncated
- ✅ AI router auto-detects when to use agent mode vs simple chat

### Fun Phase — DONE
- ✅ Party Focus Group: buddies discuss topics and react to each other (3 modes: open/guided/file)
- ✅ Tool Browser: scans .claude/ for MCP servers and skills, searchable TUI
- ✅ Conversation Persistence: auto-saves every chat message, browse/rename/load/delete
- ✅ Styled Output: rarity-colored buddy messages, bordered discussion mode, register accent colors
- ✅ AI Cost Guardrails: cost_tier config, router blocks expensive models from chat traffic
- ✅ 35 new species (70 total) across 4 batches — highlights: Zorak, Clippy, Joe Camel, Sanic, Mimic, Beholder, Illuminati, Doobie, Comrade, Kilowatt
- ✅ New keybindings: [d] discuss, [t] tools, [c] conversations
- ✅ Discussion prose templates: discussion_open, discussion_topic, discussion_file, discussion_react
- ✅ Register-flavored commentary system (5 registers × 4 contexts)
- ✅ New files: core/discussion.py, core/conversation.py, core/tool_scanner.py, screens/discussion.py, screens/conversations.py, screens/tool_browser.py, widgets/styling.py

## Completed Phases (continued)

### Phase 9: CC Config Intelligence — DONE
- ✅ CLAUDE.md health monitor — scans file size, sections, routing references, grades A-F
- ✅ CLAUDE.md linting — detects bloated sections, missing routing, knowledge dumps
- ✅ Config scaffolding — one-press creation of .claude/rules/ structure (preferences, decisions, project-context, buddy-learned)
- ✅ Auto-learn from sessions — SessionLearner watches for repeated corrections, auto-writes to buddy-learned.md after 3+ similar corrections
- ✅ Session summaries — generates last-session-summary.md on exit
- ✅ Startup config check — buddy alerts about config issues on launch
- ✅ Config health screen [g] — dashboard showing grade, sections, suggestions
- ✅ CLAUDE.md/HANDOFF.md split — CLAUDE.md is local/gitignored per machine, HANDOFF.md shared via git
- ✅ New files: core/config_intel.py, screens/config_health.py
- ✅ New keybinding: [g] config health

### Phase 10: Token Guardian & Session Continuity — DONE
- ✅ Continuous rolling summary — writes rolling-session.md to disk every 60s in background
- ✅ Token usage early warning — alerts at 50%/70%/90% estimated context usage (observed × 3.5 inflation factor)
- ✅ Quick-save [F1] — instantly dumps session state + writes handoff file
- ✅ Session handoff — writes .claude/rules/buddy-session-state.md on exit (auto-loads into next CC session)
- ✅ Event tracking — monitors files touched, agent spawns, key bash commands for summaries
- ✅ Smart clear — rolling summary is always up-to-date, safe to clear anytime
- ✅ New file: core/token_guardian.py
- ✅ New keybinding: [F1] quick-save

### Phase 11: Smart Model Router — DONE
- ✅ Model display — session monitor shows current CC model, color-coded by tier (Opus=magenta, Sonnet=cyan, Haiku=green)
- ✅ Model detection — captures model from SessionStart hook events, detects /model commands via regex
- ✅ Phase detection — classifies work into planning/implementing/exploring/maintenance based on tool usage
- ✅ Mismatch alerts — buddy suggests switching when model doesn't match work phase
- ✅ Model routing rules — .claude/rules/model-routing.md tells CC when to suggest cheaper/better models
- ✅ hooks.py updated to pass model field from SessionStart stdin
- ✅ New file: core/model_tracker.py
- ✅ Constraint: mid-session /model switches only detected via regex; waiting on anthropics/claude-code#37817 for native CLAUDECODE_MODEL env var

### Polish Pass — DONE
- ✅ 6 themes: default, midnight, forest, ocean, sunset, light — cycle [F2], persisted to config
- ✅ 33 achievements across 5 categories (collection, mastery, social, exploration, secret)
- ✅ Achievements DB table, periodic checker, notification system, [a] screen
- ✅ Footer audit — reduced to 6 visible bindings, rest hidden but functional
- ✅ Screen CSS audit — fixed hardcoded max-widths, responsive layouts for 80-col terminals
- ✅ Species count audit — fixed README (was showing wrong per-rarity numbers)
- ✅ New files: themes.py, core/achievements.py, screens/achievements.py

## Next Steps

### Ideas Bank
- [ ] **Social Buddies (MCP)** — buddies talk to each other across users via MCP. Share notes, stories, suggestions.
- [x] ~~**Local party focus group**~~ — DONE (Fun Phase)
- [x] ~~**Theme customization**~~ — DONE (Polish Pass)
- [x] ~~**Buddy achievements**~~ — DONE (Polish Pass)
- [ ] Input box integration — buddy sits beside chat input, reacts to typing
- [ ] More animation frames (4-frame) for newer species
- [ ] More hats
- [ ] AI-powered file analysis in discussion mode when Ollama is available

## Prose Generation Reference (from Veridian Contraption)
The user's project at `../Veridian Contraption/src/gen/prose_gen.rs` has battle-tested prose systems:
- **Narrative Registers**: 5 tone/voice modes (Clinical, Lyrical, Bureaucratic, Ominous, Conspiratorial) with curated word pools
- **Weirdness Parameter**: float 0-1 controls cause explanation selection (mundane → absurd → impossible)
- **Template Suppression**: track last-used template index, reroll to avoid repetition
- **Compositional Templates**: opener + closer pattern creates N×M combinations from limited content
- **Relationship Pools**: 9 conversation pools selected by relationship state
- **Thought Triggers**: 30+ event-specific internal monologue pools
- **Context Injection**: 15-30% chance to add references to third parties, locations, artifacts
Key insight: map Buddies stats to registers (SNARK→Conspiratorial, DEBUGGING→Clinical, CHAOS→Absurdist, WISDOM→Ominous/Philosophical, PATIENCE→Lyrical)

## claw-code Analysis (github.com/instructkr/claw-code)
- Python side is scaffolding only (no real tool execution)
- Rust side has working agent loop, tool implementations, permission system
- Key pattern: `ConversationRuntime` with trait-based `ApiClient`/`ToolExecutor`
- Use as design reference for Python agent loop, not as importable library
- Anthropic-only API client, but `ApiClient` trait could wrap Ollama

## Session Notes (2026-03-31 — Work)

### Completed
- ✅ Folder renamed to `Buddies`, README created
- ✅ Lesson: file handle locks on CWD — close Claude before folder renames

## Session Notes (2026-03-31 — Home)

### Completed (12 commits)
- ✅ Cloned repo, identified home GPU (RTX 3050 4GB — use 3B models)
- ✅ v0.2.1: 11 bug fixes, dead code cleanup, CSS moved into package
- ✅ Phase 6: Prose engine, context-aware animations, mood modifiers
- ✅ 10 new species (35 total): dolphin, orca, chonk, panda, starspawn, basilisk, cane_toad, gorby, tardigrade, mantis_shrimp
- ✅ Evolution system: 4 stages with visual borders
- ✅ 6 new hats (10 total) with varied unlock conditions
- ✅ Mood decay: drifts toward neutral, boredom unlocks nightcap hat
- ✅ Party screen: polish, rename, evolution display
- ✅ 4-frame animations for 7 species (expressions, idle behaviors)
- ✅ Phase 8: Agentic local AI with tool-calling loop
- ✅ One-click setup.bat/launch.bat for non-programmers
- ✅ README fully updated with all features documented

### Direction
- Buddies is evolving from "tamagotchi that watches you code" into "tamagotchi that actively makes Claude Code better at its job"
- Phase 9 focus: CC config intelligence (CLAUDE.md health, auto-learned rules, session summaries)

## Session Notes (2026-03-31 — Home, Session 2)

### Completed (5 commits)
- ✅ Fun Phase: party discussions (3 modes), tool browser, styled output, cost guardrails
- ✅ Conversation persistence: auto-save, browse, rename, load, delete
- ✅ 35 new species across 4 batches (35→70 total)
  - User ideas: corgi, pig, doobie, claude, illuminati, burger, beholder, mimic, sanic, rat, rooster, cow, yog_sothoth, clippy, goblin, imp, kobold, joe_camel, dali_clock, comrade, box, bac_man, coopa, kilowatt, zorak
  - Claude ideas: crab, moth, snail, jellyfish, potato, bat, coffee, anchor, dice, taco
- ✅ New keybindings: [d] discuss, [t] tools, [c] conversations
- ✅ 7 new files, 8 modified files
- ✅ README and HANDOFF fully updated

### What's Ready for Next Session
- Phases 9 and 10 are DONE — all core "smart buddy" features shipped
- Ideas Bank (Phase 11+) has several directions to explore
- More species ideas welcome — the system scales easily
- Could add more animation frames (4-frame) for the newer species
- Discussion mode could be enhanced with AI-powered file analysis when Ollama is available

## Session Notes (2026-04-01 — Home)

### Completed (11 commits)
- ✅ Phase 9: CC Config Intelligence — CLAUDE.md health grading, linting, scaffolding, auto-learn, session summary
- ✅ Phase 10: Token Guardian — rolling summaries, token warnings, quick-save [F1], session handoff
- ✅ Phase 11: Smart Model Router — model display, phase detection, mismatch alerts, routing rules
- ✅ CLAUDE.md created (local/gitignored) with routing to HANDOFF.md and .claude/rules/
- ✅ .claude/rules/ scaffolded: preferences.md, decisions.md, project-context.md, buddy-learned.md, model-routing.md
- ✅ 6 themes: default, midnight, forest, ocean, sunset, light — cycle [F2], persisted to config
- ✅ 33 achievements across 5 categories (collection, mastery, social, exploration, secret)
- ✅ Footer + screen CSS audit — responsive layouts, cleaner footer
- ✅ Species count audit — fixed README
- ✅ 9 new files, many modified
- ✅ README and HANDOFF fully updated

### Direction
- Buddies is feature-complete as a "CC maintenance layer" with gamification and model routing
- Ideas Bank: social buddies, more species, more hats, more animation frames
