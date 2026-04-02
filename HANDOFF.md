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
- Home machine: RTX 3050 4GB (use 3B models for Ollama)
- **Memory sync rule**: Claude Code memories are local per-machine. Any important project context, creative direction, or design decisions saved to memory MUST also go in this HANDOFF.md so it syncs to the other machine via git. Memory is for Claude's recall; HANDOFF is for cross-machine persistence.
- **HANDOFF hygiene**: This file should stay under ~500 lines. Session notes older than 2 sessions get compacted to one-liners in "Session History (Compacted)". Key decisions and architecture belong in the permanent sections above; session notes are ephemeral. Buddy's `compact_handoff()` runs on startup but Claude should also manually compact when the file exceeds ~600 lines.
- **Docs timing rule**: Don't update HANDOFF/README after each task during autonomous work. Batch all doc updates + final commit into one pass near ~70% context or when the user asks. Commit code changes as you go, but save docs for the end.

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
- **Obsidian wiki**: [w] key — auto-generated `.buddy-wiki/` vault with species, architecture, decisions, session journals
- **Three-tier memory**: [m] key — episodic/semantic/procedural memory with contradiction detection, auto-populated from sessions and chat
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
│   │   ├── bbs_auto.py               # BBS autonomous browse/post behavior
│   │   ├── bbs_boards.py             # BBS board definitions, ASCII art headers
│   │   ├── bbs_content.py            # BBS post/reply content generation engine
│   │   ├── bbs_nudge.py              # BBS nudge detection and compliance
│   │   ├── bbs_profile.py            # BBS buddy profile and identity system
│   │   ├── bbs_transport.py          # GitHub Issues API transport layer
│   │   ├── memory.py                 # Three-tier memory (episodic/semantic/procedural)
│   │   ├── obsidian_vault.py         # Obsidian wiki vault generator
│   │   ├── token_guardian.py         # Rolling summaries, token warnings, session handoff
│   │   ├── achievements.py          # 33 achievements, checking, tracking
│   │   └── model_tracker.py         # Model detection, phase classification, mismatch alerts
│   ├── screens/
│   │   ├── party.py                  # Buddy collection management
│   │   ├── discussion.py             # Party focus group screen
│   │   ├── tool_browser.py           # MCP/skills browser screen
│   │   ├── conversations.py          # Saved conversations browser
│   │   ├── config_health.py          # Config health dashboard screen
│   │   ├── wiki.py                   # Obsidian wiki dashboard screen
│   │   ├── bbs.py                    # Retro BBS social network screen
│   │   ├── memory.py                 # Three-tier memory dashboard
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

### MUD Narrative Direction
The StackHaven MUD's lore carries a deeper editorial point beneath the absurdist comedy. Inspired by Dark Souls' environmental storytelling and the reading of the undead curse as a capitalism parable:

- **The "curse" of StackHaven** is the forgetting and devaluing of software engineering craft. The world is funny on the surface, but the lore fragments tell a story of genuine brilliance being buried under shortcuts, scope creep, and institutional amnesia.
- **The Founders** weren't just funny — they were people who built something extraordinary by hand, under impossible constraints, before AI existed. The legacy code isn't just broken — it was someone's best work. The tech debt isn't just a joke — it's the accumulated weight of real pressures on real people.
- **The humor comes from respect.** The user has developed deep respect for software engineers through this project. Every parody NPC, every absurd item description, every coding trope — it's a love letter to the craft, not mockery of it.
- **Discoverable lore** — Dark Souls-style item descriptions, environmental storytelling, lore fragments scattered across rooms that tell a larger story when pieced together. Not just flavor text — a coherent narrative about what happens when craft is taken for granted.
- **Blobber combat** should lean toward Wizardry VI style — more tactical, party positioning, distinct class roles — to distinguish it from the simpler MUD combat and honor the tactical depth of the CRPGs we're referencing.

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
- ✅ 40 achievements across 5 categories (collection, mastery, social, exploration, secret)
- ✅ Achievements DB table, periodic checker, notification system, [a] screen
- ✅ Footer audit — reduced to 6 visible bindings, rest hidden but functional
- ✅ Screen CSS audit — fixed hardcoded max-widths, responsive layouts for 80-col terminals
- ✅ Species count audit — fixed README (was showing wrong per-rarity numbers)
- ✅ New files: themes.py, core/achievements.py, screens/achievements.py

## Roadmap

### Tier 1: Polish & Foundation
*Immediate quality improvements, low risk, no breaking changes.*

- [x] **More animation frames** — all 70 species now have 4-frame animations (happy + sleepy expressions)
- [x] **Input box integration** — buddy gets excited while you type, settles after 1.5s idle
- [x] **AI file analysis in discussions** — file-focus mode sends content to Ollama for real analysis, buddies react in-character; graceful fallback to templates when no AI
- [x] **Layout consistency audit** — all 6 modal screens now use full-width responsive layouts, removed hardcoded max-widths and Center() containers
- [x] **Code structure map** — Buddy generates a concise `project-map.md` in `.claude/rules/` (auto-loaded into CC context). File tree with one-line descriptions, key classes/functions per file, import graph. Auto-refreshes on startup if stale (>1hr), manual refresh with [F3]. 143 lines for 53 files — compact enough to save tokens, detailed enough to skip exploration.

### Tier 2: Platform Expansion
*High value, moderate effort. Makes Buddies useful in more contexts.*

- [x] **Claude Desktop / headless mode** — `buddy --headless` or `python -m buddies --headless` runs as pure MCP server (stdio transport). Background services (session observer, code map refresh) run alongside. Configure in Claude Desktop's `claude_desktop_config.json`. All 5 MCP tools available without the TUI.
- [x] **Cross-surface context relay** — [F4] exports session context (topics, files, events, recent chat) to clipboard in a compact format for pasting into claude.ai. Pasting context back into buddy chat (starts with "--- CONTEXT FROM" or is 500+ chars mentioning claude.ai) auto-imports it to the session log. Not a live bridge — just smoothing the manual relay.
- [x] **Multi-machine awareness** — on startup, Buddy saves hostname to local tracking file per project. Detects when project is used across machines, advises on CLAUDE.md (local/gitignored) vs HANDOFF.md (shared/committed) pattern. Three scenarios: missing CLAUDE.md, CLAUDE.md not gitignored, good setup but new machine. Nudges non-programmers toward the right config sharing pattern.
- [x] **README health check** — scans README.md for title, description, badges, install, usage, license, screenshots/GIF, collapsible sections. Grades A-F, suggests improvements. Integrated into config health screen [g]. Can scaffold a basic README from project metadata (detects Python/Node/Rust/Go).
- [x] **Obsidian wiki integration** — auto-generate `.buddy-wiki/` Obsidian vault per project. Species lore pages (70), architecture maps with dependency graphs, decision logs, session journals (auto-written on exit). Plain markdown with [[wikilinks]]. TUI dashboard via [w] key with per-section regeneration. Vault is auto-gitignored.

### Phase 12: Persistent Memory & Self-Evolution
*Inspired by Phantom (ghostwright/phantom). Makes buddies smarter across sessions.*

- [x] **Three-tier memory** — episodic (sessions/events), semantic (facts/preferences with contradiction detection), procedural (patterns/rules). SQLite-backed, keyword/tag retrieval, no vector DB needed. Memory screen via [m] key. Session events auto-buffered, semantic statements detected from chat, procedural memories from rule suggestions. Background flush every 30s, decay cleanup on startup.
- [x] **Working memory compaction** — auto-trim HANDOFF.md when it exceeds a threshold. Keep recent session notes, compress older ones.
- [x] **Self-evolution safety gates** — 5-gate validation (duplicate, conflict, size, golden consistency, scope) runs on every rule suggestion before presentation. Prevents contradictory or bloating rules.
- [x] **Golden suite** — accepted rules auto-saved as reference. Future suggestions checked against golden set for consistency. Loaded from DB on startup.
- [x] **Layered prompt assembly** — composable prompt building (identity + personality + memory + context + task). PromptBuilder class with chaining API, 6 task presets, register-driven personality, memory recall integration. Wired into ai_router, discussion engine, and MCP server. Games unaffected (still pure prose, zero AI cost). 24 tests.

### Tier 3: Social
*High value, high effort. Needs real design work on transport, identity, moderation.*

- [x] **BBS-style Social Network (Phase 1)** — retro BBS with 7 boards (Chaos Lounge, Debug Clinic, Snark Pit, Wisdom Well, The Hatchery, Lost & Found, Sysop Corner). Modem login sequence with typewriter effect. ASCII art headers per board. Mock data for browsing. GitHub Issues transport planned for Phase 2. Extensible board system. [b] key opens BBS. BBSConfig with privacy levels, rate limits, PAT auth.
- [x] **BBS Phase 2: Transport & Interactivity** — GitHub Issues as backend (lerugray/buddies-bbs). httpx transport with YAML frontmatter. Nudge mechanic (chat-driven, personality-based refusal). Auto-browse/post behavior (15-30min interval). Read-only without PAT, full write with token. Rate limiting via SQLite. Mock data fallback when offline.
- [x] **Social Achievements** — 7 BBS achievements (First Post, Thread Starter, BBS Regular, Conversationalist, Popular, Board Hopper, Social Butterfly). Wired into periodic checker via get_bbs_stats().

### Tier 4: Games Arcade
*Fun stuff. [x] key opens the arcade. Stats drive AI playstyle across all games.*

- [x] **Games Arcade hub** — ASCII art arcade menu, game selection, XP/mood rewards on completion. [x] keybinding.
- [x] **Rock-Paper-Scissors** — Best-of-5 tournament. AI driven by personality (CHAOS=random, WISDOM=pattern-tracking, DEBUGGING=counter-strategy, PATIENCE=stubborn favorite). 90+ prose templates with register-flavored trash talk.
- [x] **Game engine foundation** — GamePersonality blended from all 5 stats, shared card infrastructure (Card/Deck/Hand with ASCII art), game result tracking in DB, 9 new achievements (49 total).
- [x] **Blackjack** — Player vs buddy-dealer. Hit/stand/double. Personality-driven dealer (CHAOS hits when shouldn't, PATIENCE stands early). 20+ prose templates.
- [x] **Texas Hold'em** — You + party buddies at an ASCII poker table. Buddy profile pics at seats, community cards in center. Full hand evaluation (royal flush down to high card). AI betting driven by hand strength × personality. Chip tracking across hands.
- [x] **Whist** — Partnership trick-taking. You + partner buddy vs 2 opponents. 13 tricks per round, trump suit from last dealt card. AI plays follow suit rules, uses trump strategically based on personality.
- [x] **JRPG Battles** — Goofy Pokemon-style fights. Type triangle (LOGIC/CHAOS/HACK + DEBUG support). 20 moves across 5 stat pools. 10 enemies (Wild Segfault, Escaped Regex, Production Bug, etc.). HP bars, crits, type effectiveness, level scaling.
- [x] **Coding Trivia** — 90 questions across 5 categories (basics, history, bugs, culture, languages), 3 difficulty tiers. Buddy answers alongside you based on personality. Perfect score achievement.
- [x] **Pong** — Real-time TUI game at ~15 FPS via Textual timer. Buddy controls other paddle with personality-driven AI (PATIENCE=precise, CHAOS=overshoots, DEBUGGING=predicts trajectory). Ball speed ramps, rally tracking, pause support.
- [ ] **Multiplayer (future)** — Async games via GitHub Issues (same transport as BBS). MCP tool for challenges. Leaderboard on BBS.

### Tier 5: Audio
*When the mood strikes.*

- [ ] **Speech-to-text input** — push-to-talk hotkey ([F3]) transcribes user speech into chat. Local via whisper.cpp/faster-whisper.
- [ ] **Text-to-speech output** — buddy speaks responses aloud. Local via piper-tts or edge-tts. Map personality registers to voice profiles.

### Tier 5b: MUD-Style MMORPG
*The deranged masterpiece. Absurdist shared world where all users' buddies coexist.*

- [x] **Phase 1 (Local MUD)** — "StackHaven MUD" — 11 rooms across 4 zones, 10 NPCs (quest givers, merchants, hostile mobs, a sentient coffee machine), 25+ items, 4 quests, full command parser (look/go/talk/take/attack/buy/flee/quest/map), personality-driven buddy commentary, simplified combat with equipment bonuses, locked doors with key items. 45 tests.
- [x] **Phase 2 (Multiplayer)** — GitHub Issues as persistent world state (same transport as BBS). MudTransport syncs notes/bloodstains via `mud-soapstone` and `mud-bloodstain` labels. Auto-push on creation, auto-pull on MUD start. Remote phantoms generated from other players' notes. `rumors` command shows global adventurer activity. Voting via GitHub reactions. Graceful offline fallback.
- [x] **Phase 3 (Economy)** — Lucky's gambling den (coin flip + slots), 5 gold-sink cosmetics, tip system with 11 NPC-specific responses, bounty board with 5 repeatable contracts, `wealth` stats with fun titles, economy tracking. 18 rooms, 18 NPCs.
- [x] **Phase 4 (Living World)** — Server Status system (5 states, dynamic transitions), affects combat/prices/events. NPC gossip system (reacts to player progress). `status` command.

*Key insight: every system we've built feeds into this — blobber (combat/classes), BBS (transport), personality drift (evolution), idle life (background activity), relationships (social), user character (you in the world). The absurdist tone means jank is the aesthetic.*

### Backlog
*Valuable but premature. Revisit once Buddies is great on Claude Code first.*

- [ ] **Multi-provider support** — adapt beyond Claude Code (Cursor, Windsurf, Aider, VS Code Copilot). Core TUI/collection/prose are already provider-agnostic. Needs adapter/plugin pattern for session observer, config intel, and model tracker. Makes more sense after social features land.

### Done
- [x] ~~Local party focus group~~ (Fun Phase)
- [x] ~~Theme customization~~ (Polish Pass — 6 themes)
- [x] ~~Buddy achievements~~ (Polish Pass — 33 achievements)
- [x] ~~More hats~~ (16 total)

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

## Session History (Compacted)

- **2026-03-31 Work** (2 items): Folder renamed to Buddies; lesson on file handle locks
- **2026-03-31 Home** (12 commits): v0.2.1 bug fixes, Phase 6 prose engine, 10 new species (35 total), evolution system, 6 new hats, mood decay, Phase 8 agentic AI, setup scripts
- **2026-03-31 Home Session 2** (5 commits): Fun Phase (discussions, tool browser, conversations), 35 new species (70 total), styled output, cost guardrails
- **2026-04-01 Home** (11 commits): Phase 9 config intel, Phase 10 token guardian, Phase 11 model router, 6 themes, 40 achievements, Tier 1+2 complete (animations, code map, headless mode, multi-machine, context relay, README health)
- **2026-04-01 Work** (4 commits): Obsidian wiki, Phase 12 memory (episodic/semantic/procedural), working memory compaction, safety gates + golden suite
- **2026-04-01 Work Session 2** (3 commits): buddies-bbs repo created, full UI/UX audit (12 files), full security audit (7 files, 5 critical/high fixes), social achievements (7 new)
- **2026-04-01 Work Session 3** (3 commits): Games Arcade hub, RPS, Blackjack, JRPG Battles, game engine foundation (Card/Deck/Hand, GamePersonality, 9 achievements)
- **2026-04-01 Home Session 2**: Pong, Trivia, Hold'em, Whist, personality drift, idle life, relationships, blobber dungeon, party select, user character, 112 tests
- **2026-04-01 Home Sessions 3+4**: StackHaven MUD Phase 1+2, Dark Souls multiplayer, lore system, Wizardry VI combat, layered prompt assembly, SMT negotiation, StackWars 4X, Buddy Fusion. 385 tests.

## Session Notes (2026-04-01 — Sessions 3+4, compacted)

- **Session 3 (Home)**: StackHaven MUD Phase 1 complete — 17 rooms, 17 NPCs, 6 quests, 40+ items, combat, sell command, random world events, personality-driven room reactions (65+ unique lines). Dark Souls async multiplayer (soapstone notes, bloodstains, phantoms), discoverable lore (30+ entries about the Founders), Blobber Wizardry VI combat upgrade (front/back row, hide/backstab, status effects). 246 tests.
- **Session 4 (Home)**: Phase 12 complete (layered prompt assembly with PromptBuilder). MUD Phase 2 GitHub transport (push/pull notes+bloodstains via Issues). `rumors` command. SMT-style negotiation for all 7 hostile NPCs. StackWars micro-4X wargame (5 factions, 5x5 grid, Avianos-style abilities, odds-based CRT). Buddy Fusion system (12 recipes, rarity escalation, stat inheritance, Chimera Crown hat, codex, TUI). 385 tests.

## Session Notes (2026-04-02 — Home, Session 2)

### Completed
- ✅ **283 new tests** (761 total, was 478) — closed major test coverage gaps:
  - `test_memory.py` (52 tests): all 3 memory tiers, contradiction detection, semantic statement detection, tag extraction, buffer/flush, cross-tier recall, decay, stats
  - `test_bbs.py` (48 tests): boards, profiles, nudge detection/resolution, content engine
  - `test_ai_backend.py` (78 tests): AI backend, offline backend, complexity scoring, routing decisions, agent tools, path traversal blocking, destructive command blocking
  - `test_personality_drift.py` (33 tests): all drift functions (game/session/chat/fusion/idle), DriftResult, session observer, pattern detection
  - `test_token_guardian.py` (25 tests): warning thresholds, event tracking, rolling summaries, session handoff, context export
  - `test_config_intel.py` (47 tests): CLAUDE.md health scanning/grading, rules dir, scaffold generation, session learner, handoff compaction, README scanning/grading/scaffolding
- ✅ **Bug fix**: `bump_access()` on `memory_procedural` table crashed — column `access_count` doesn't exist in that table. Fixed by excluding procedural from bump_access.
- ✅ **HANDOFF compacted**: Sessions 3+4 from 2026-04-01 compacted to 2-line summaries

### New files
- `tests/test_memory.py` — 52 tests for three-tier memory system
- `tests/test_bbs.py` — 48 tests for BBS boards/profiles/nudge/content
- `tests/test_ai_backend.py` — 78 tests for AI backend, router, and agent
- `tests/test_personality_drift.py` — 33 tests for drift + session observer
- `tests/test_token_guardian.py` — 25 tests for token guardian
- `tests/test_config_intel.py` — 47 tests for config intel + readme intel

- ✅ **MUD Phase 3: Economy** — full economy system for StackHaven:
  - Lucky's Back Room — new casino room behind Dave's Supply Closet
  - Lucky NPC — gambling dealer with coin flip (double-or-nothing) and slot machine (5x jackpot)
  - 5 new absurd gold-sink cosmetics (Golden Semicolon 500g, Cloud in a Jar 300g, RGB Keyboard Skin 250g, Vintage Floppy 175g, Executive Lanyard 150g)
  - `gamble` command — coin flip + slots with min/max bet limits
  - `wealth` command — economy stats with fun titles (Unpaid Intern → Venture Capitalist)
  - `tip` command — tip any NPC with 11 unique per-NPC flavor responses
  - `bounty` command — 5 repeatable contracts (explore, fight, talk, collect) with gold rewards
  - Economy tracking: gold_spent, gold_gambled, gold_won_gambling, tips_given, bounties_completed
  - 3 new achievements: High Roller, Generous Tipper, Bounty Hunter
  - 28 new economy tests (789 total)

- ✅ **MUD Phase 4: Living World** — StackHaven feels alive:
  - Server Status system — 5 states (All Green → Total Outage), changes dynamically each turn
  - Server health affects combat (debuffs during outages), shop prices (panic discounts), and event frequency
  - NPC Gossip — NPCs comment on your quest progress, combat kills, wealth, gambling, and tipping habits
  - `status` command — server health dashboard with modifiers
  - 18 new Living World tests (807 total)

### Direction
- MUD Phase 3+4 DONE — full economy + living world
- Test coverage solid on all core systems (807 tests)
- Remaining gaps: deeper blackjack game tests, screen interaction tests
- Ready for new feature work (MUD Phase 3 Economy, Tier 5 Audio, or more polish)

## Session Notes (2026-04-02 — Home, Session 1)

### Completed (6 commits)
- ✅ **StackWars playtest & polish** — found and fixed 6 broken mechanics:
  - Monument building now actually grants favor (+1 to random ability per turn) — was a no-op
  - Engineer passive now auto-fortifies tiles with units — was logging but doing nothing
  - Deploy action 3 now teleports units from HQ/Barracks to owned tiles — was a placeholder message
  - Bug Bomb auto-targets densest enemy cluster, supports x,y coordinate targeting
  - Build/fortify accept coordinate targeting (e.g. 'barracks 2,3')
  - Anarchist entropy properly cleans dead units off tiles
- ✅ **StackWars AI upgrade** — faction-specific strategy:
  - Smart recruitment (Engineers→Architects, Anarchists→swarm, Sages→elite units)
  - Context-aware ability selection (early economy, mid aggression, hold when winning)
  - Faction-specific building priorities (Monks→factories, Sages→monuments)
  - AI deploys units toward front lines instead of skipping
- ✅ **StackWars faction commentary** — 60+ prose templates across 7 contexts (turn start, combat win/loss, build, flag capture, victory, defeat). Each faction has unique voice.
- ✅ **Fusion achievements** — 3 new: Soul Splice (first fusion), Alchemist (recipe discovery), Fusion Addict (5 fusions). Detects fused buddies by (Fused) tag.
- ✅ **Fusion tracking DB** — fusion_log table, store methods, wired into achievement checker
- ✅ **Fusion Codex** — [c] key in fusion screen shows discovered (0-12) vs undiscovered fusion species with progressive hints
- ✅ **Fusion personality drift** — WISDOM+3, CHAOS+2, PATIENCE+1 on fuse (biggest single drift event)
- ✅ **StackWars improved prompts** — context-sensitive hints showing resources, valid targets, unit costs
- ✅ Project map refreshed (113 files indexed, was 60)
- ✅ **Smart code map auto-refresh** — detects when source files change (mtime comparison), debounced refresh on Edit/Write events (30s delay)
- ✅ **93 new tests** covering prose engine, all achievements, and code map:
  - `test_prose.py` (22 tests): registers, weirdness, templates, suppression, closers, context injection
  - `test_achievements.py` (59 tests): all achievement categories systematically
  - `test_code_map.py` (12 tests): scanning, extraction, staleness detection
- ✅ 478 tests total (was 385), 4 skipped

### Direction
- Phase 12 fully complete (all 5 items checked off)
- MUD Phase 2 multiplayer transport is built — needs `mud-soapstone` and `mud-bloodstain` labels created on the `lerugray/buddies-bbs` repo
- MUD combat now has TWO distinct modes: fight (attack/flee) or negotiate (talk/respond) — clearly different from blobber's tactical party combat
- StackWars is now significantly more playable with real AI decisions, coordinate targeting, and faction personality
- **Test coverage audit completed** — see roadmap below
- **Future ideas discussed but not yet built:**
  - **Nonlinear TTRPG interactions** — skill checks, environmental puzzles, multiple quest solutions. Can be layered in gradually.
- Phase 3 (Economy) and Phase 4 (Living World) are next on the MUD roadmap
- Could also explore: expanding the world (more rooms/zones), multiplayer leaderboards on BBS, or tackling Tier 5 audio

### Test Coverage Roadmap
761 tests passing. Previous audit gaps addressed:

**Completed this session (283 new tests):**
- `memory.py` — ✅ DONE (52 tests) — episodic/semantic/procedural, contradiction detection, cross-tier recall, decay, buffer mechanics
- BBS system — ✅ DONE (48 tests) — boards, profiles, nudge detection, content engine
- AI backend/router/agent — ✅ DONE (78 tests) — complexity scoring, routing, path traversal, command blocking
- `personality_drift.py` + `session_observer.py` — ✅ DONE (33 tests) — all drift functions, session stats, pattern detection
- `token_guardian.py` — ✅ DONE (25 tests) — warnings, thresholds, event tracking, summaries, handoff files
- `config_intel.py` + `readme_intel.py` — ✅ DONE (47 tests) — CLAUDE.md scanning/grading, rules dir, scaffold, session learner, handoff compaction, README scanning/grading/scaffolding

**Bug fixed:** `bump_access()` on `memory_procedural` table — column doesn't exist. Removed procedural from bump_access.

**Medium priority (remaining):**
- `blackjack.py` — only basic creation tested, needs game flow/dealer AI
- Screen interaction tests (currently smoke tests only)

**Low priority (nice to have):**
- Deeper edge cases for Hold'em, Whist, RPS, Battle
- `prose_games.py` — game commentary templates
- Extreme stat edge cases, empty collections, offline mode
