# Project Map

Auto-generated code structure for AI navigation. 53 files indexed.

## File Tree

### (root)/
- `CLAUDE.md` (27L) — This file is gitignored. Each machine gets its own copy.
- `HANDOFF.md` (431L) — **Folder Status**: ✅ Renamed to `Buddies` (2026-03-31)
- `README.md` (323L) — A tamagotchi-style AI companion that lives in your terminal and watches your Cla

### buddies/
- `launch.sh` (11L)
- `pyproject.toml` (27L) — toml config
- `setup.sh` (40L)

### buddies\src\buddies/
- `__init__.py` (4L) — Buddy — A tamagotchi-style AI companion for Claude Code.
- `__main__.py` (6L) — Allow running buddies as: python -m buddies
- `app.py` (1084L) — Buddy — Main Textual TUI application.
- `config.py` (83L) — Configuration and settings for Buddy.
- `first_run.py` (180L) — First-run setup screen — species selection with gacha mechanics.
- `setup_hooks.py` (115L) — Setup script to register Buddy's hooks with Claude Code.
- `setup_mcp.py` (79L) — Register Buddy's MCP server with Claude Code.
- `themes.py` (113L) — Theme definitions for Buddies TUI.

### buddies\src\buddies\art/
- `__init__.py` (1L)
- `sprites.py` (4427L) — Colored 8-bit pixel art sprites using Unicode half-blocks and Rich markup.

### buddies\src\buddies\core/
- `__init__.py` (1L)
- `achievements.py` (207L) — Achievements system — track milestones and reward exploration.
- `agent.py` (476L) — Agentic tool loop — gives the local AI model real capabilities.
- `ai_backend.py` (193L) — Flexible AI backend — connects to Ollama, OpenAI-compatible APIs, or runs offline.
- `ai_router.py` (261L) — Query complexity router — decides whether to handle locally or flag for Claude.
- `buddy_brain.py` (366L) — Buddy's personality, stats, species, and evolution logic.
- `code_map.py` (330L) — Code Structure Map — generates a concise project-map.md for AI consumption.
- `config_intel.py` (543L) — Config Intelligence — CLAUDE.md health, linting, scaffolding, and session learning.
- `conversation.py` (200L) — Conversation persistence — auto-save, load, rename, delete chat history.
- `discussion.py` (411L) — Multi-buddy discussion engine — party focus group conversations.
- `hooks.py` (98L) — Claude Code hook receiver.
- `model_tracker.py` (292L) — Model Tracker — detect current CC model and classify work phases.
- `prose.py` (422L) — Personality-driven prose engine for buddy thoughts and commentary.
- `rule_suggester.py` (209L) — Rule suggestion engine — detects patterns and suggests Claude Code config improvements.
- `session_observer.py` (286L) — Session observer — watches Claude Code events and detects patterns.
- `token_guardian.py` (269L) — Token Guardian — rolling session summaries, token warnings, and session handoff.
- `tool_scanner.py` (134L) — Scans for installed MCP servers and Claude Code skills.

### buddies\src\buddies\db/
- `__init__.py` (1L)
- `models.py` (67L) — SQLite schema and database initialization.
- `store.py` (194L) — Data access layer for Buddy's SQLite database.

### buddies\src\buddies\mcp/
- `__init__.py` (1L)
- `server.py` (232L) — Buddy MCP Server — exposes tools to Claude Code.

### buddies\src\buddies\screens/
- `__init__.py` (2L) — Buddy screens — additional UI panels beyond the main app.
- `achievements.py` (155L) — AchievementsScreen — view unlocked and locked achievements.
- `config_health.py` (266L) — ConfigHealthScreen — CLAUDE.md health dashboard and config scaffolding.
- `conversations.py` (241L) — ConversationsScreen — browse, load, rename, and delete saved conversations.
- `discussion.py` (238L) — DiscussionScreen — party focus group conversations.
- `party.py` (352L) — PartyScreen — manage your buddy collection.
- `tool_browser.py` (187L) — ToolBrowserScreen — browse installed MCP servers and skills.

### buddies\src\buddies\widgets/
- `__init__.py` (1L)
- `buddy_display.py` (212L) — Buddy display widget — shows the pixel art sprite, stats, and mood.
- `chat.py` (95L) — Chat widget — interact with buddy / local AI.
- `session_monitor.py` (107L) — Session monitor widget — shows Claude Code activity feed.
- `styling.py` (96L) — Centralized styling utilities for buddy messages and UI elements.

### session-notes/
- `2026-03-31-session-1.md` (36L) — - **Buddy** — tamagotchi-style local AI companion for Claude Code
- `2026-03-31-session-2.md` (80L) — Transformed **Buddy** into **BUDDIES** — a full multi-buddy collection system wi
- `PLAN-buddies-refactor.md` (106L) — The current single-buddy model (enforced by `CHECK (id = 1)` in the DB) limits t

## Key Symbols

- **buddies/src/buddies/app.py**: classes: BuddyApp
- **buddies/src/buddies/config.py**: classes: AIBackendConfig, BuddyConfig | fns: get_data_dir
- **buddies/src/buddies/first_run.py**: classes: HatchScreen
- **buddies/src/buddies/setup_hooks.py**: fns: get_claude_settings_path, get_hook_command, setup_hooks, remove_hooks
- **buddies/src/buddies/setup_mcp.py**: fns: get_claude_settings_path, setup_mcp, remove_mcp
- **buddies/src/buddies/themes.py**: fns: get_theme, next_theme
- **buddies/src/buddies/core/achievements.py**: classes: Achievement
- **buddies/src/buddies/core/agent.py**: classes: ToolResult | fns: execute_tool
- **buddies/src/buddies/core/ai_backend.py**: classes: AIResponse, AIBackend, OfflineBackend | fns: create_backend
- **buddies/src/buddies/core/ai_router.py**: classes: RoutingDecision, AIRouter
- **buddies/src/buddies/core/buddy_brain.py**: classes: Rarity, Species | fns: get_mood_modifier, mulberry32, hash_seed, pick_species, get_mood, calculate_level, xp_for_next_level, get_evolution_stage, check_evolution, check_hat_unlock
- **buddies/src/buddies/core/code_map.py**: classes: FileInfo | fns: scan_project, generate_project_map
- **buddies/src/buddies/core/config_intel.py**: classes: Section, ClaudeMdReport, RulesDirReport, ConfigReport, ConfigIntelligence
- **buddies/src/buddies/core/conversation.py**: classes: Message, ConversationMeta, ConversationLog | fns: list_conversations, delete_conversation, rename_conversation
- **buddies/src/buddies/core/discussion.py**: classes: DiscussionMessage, DiscussionEngine
- **buddies/src/buddies/core/hooks.py**: fns: get_events_path, write_event, main
- **buddies/src/buddies/core/model_tracker.py**: classes: PhaseChange, ModelTracker | fns: classify_model
- **buddies/src/buddies/core/rule_suggester.py**: classes: RuleSuggestion, RuleSuggester
- **buddies/src/buddies/core/session_observer.py**: classes: SessionEvent, SessionStats, SessionObserver
- **buddies/src/buddies/core/token_guardian.py**: classes: TokenWarning, TokenGuardian
- **buddies/src/buddies/core/tool_scanner.py**: classes: ToolInfo | fns: scan_all_tools
- **buddies/src/buddies/db/store.py**: classes: BuddyStore
- **buddies/src/buddies/mcp/server.py**: fns: buddy_status, buddy_note, session_stats, ask_buddy, get_buddy_notes, main
- **buddies/src/buddies/screens/achievements.py**: classes: AchievementsScreen
- **buddies/src/buddies/screens/config_health.py**: classes: ConfigHealthScreen
- **buddies/src/buddies/screens/conversations.py**: classes: ConversationsScreen
- **buddies/src/buddies/screens/discussion.py**: classes: DiscussionScreen
- **buddies/src/buddies/screens/party.py**: classes: PartyScreen
- **buddies/src/buddies/screens/tool_browser.py**: classes: ToolBrowserScreen
- **buddies/src/buddies/widgets/buddy_display.py**: classes: SpriteDisplay, StatsDisplay, BuddyDisplay
- **buddies/src/buddies/widgets/chat.py**: classes: ChatWindow
- **buddies/src/buddies/widgets/session_monitor.py**: classes: SessionMonitor
- **buddies/src/buddies/widgets/styling.py**: fns: format_system_message

## Internal Dependencies

- `buddies/src/buddies/__main__.py` ← buddies.app
- `buddies/src/buddies/app.py` ← buddies.config, buddies.core.achievements, buddies.core.ai_backend, buddies.core.ai_router, buddies.core.buddy_brain, buddies.core.code_map, buddies.core.config_intel, buddies.core.conversation, buddies.core.model_tracker, buddies.core.prose, buddies.core.rule_suggester, buddies.core.session_observer, buddies.core.token_guardian, buddies.db.store, buddies.first_run, buddies.screens.achievements, buddies.screens.config_health, buddies.screens.conversations, buddies.screens.discussion, buddies.screens.party, buddies.screens.tool_browser, buddies.themes, buddies.widgets.buddy_display, buddies.widgets.chat, buddies.widgets.session_monitor
- `buddies/src/buddies/first_run.py` ← buddies.art.sprites, buddies.core.buddy_brain
- `buddies/src/buddies/core/achievements.py` ← buddies.core.buddy_brain
- `buddies/src/buddies/core/agent.py` ← buddies.core.ai_backend
- `buddies/src/buddies/core/ai_backend.py` ← buddies.config
- `buddies/src/buddies/core/ai_router.py` ← buddies.core.agent, buddies.core.ai_backend, buddies.core.buddy_brain
- `buddies/src/buddies/core/conversation.py` ← buddies.config
- `buddies/src/buddies/core/discussion.py` ← buddies.core.ai_backend, buddies.core.buddy_brain, buddies.core.prose
- `buddies/src/buddies/core/hooks.py` ← buddies.config
- `buddies/src/buddies/core/model_tracker.py` ← buddies.config
- `buddies/src/buddies/core/prose.py` ← buddies.core.buddy_brain
- `buddies/src/buddies/core/rule_suggester.py` ← buddies.core.session_observer, buddies.db.store
- `buddies/src/buddies/core/session_observer.py` ← buddies.core.hooks
- `buddies/src/buddies/core/token_guardian.py` ← buddies.config
- `buddies/src/buddies/db/store.py` ← buddies.db.models
- `buddies/src/buddies/mcp/server.py` ← buddies.config, buddies.core.ai_backend, buddies.core.hooks, buddies.db.store
- `buddies/src/buddies/screens/achievements.py` ← buddies.core.achievements
- `buddies/src/buddies/screens/config_health.py` ← buddies.core.config_intel
- `buddies/src/buddies/screens/conversations.py` ← buddies.core.conversation
- `buddies/src/buddies/screens/discussion.py` ← buddies.core.ai_backend, buddies.core.buddy_brain, buddies.core.discussion, buddies.core.prose, buddies.db.store, buddies.widgets.styling
- `buddies/src/buddies/screens/party.py` ← buddies.core.buddy_brain, buddies.db.store, buddies.widgets.styling
- `buddies/src/buddies/screens/tool_browser.py` ← buddies.core.tool_scanner
- `buddies/src/buddies/widgets/buddy_display.py` ← buddies.art.sprites, buddies.core.buddy_brain
- `buddies/src/buddies/widgets/chat.py` ← buddies.widgets.styling
