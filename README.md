# 🐾 Buddies — Your Local AI Companion Collection

A tamagotchi-style AI companion that lives in your terminal and watches your Claude Code sessions. Hatch buddies, collect species, earn hats, and build a team of quirky little creatures that react to how you code.

![Buddies TUI — early version](screenshot.jpg)

## What You Get

- **35 species** to collect — from common Gorby to Legendary Starspawn
- **Personality stats** (DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE) that evolve as you code
- **Buddy thoughts** — personality-driven ambient commentary during sessions, flavored by stats and mood
- **Hats & cosmetics** unlocked by playstyle — crown for debuggers, wizard hat for thinkers, propeller for chaos agents
- **Multi-buddy collection** — hatch new buddies, switch between them, customize names
- **Session awareness** — your buddy watches Claude Code activity, detects patterns, suggests config rules
- **Local AI brain** — connects to Ollama or any OpenAI-compatible API for personality responses (works offline too)
- **Zero token cost** — everything runs locally except tiny MCP payloads to Claude

## Quick Start

### 1. Install

```bash
cd buddies
pip install -e .
```

### 2. Launch

```bash
# From anywhere after install
buddy

# Or from the buddies folder
python -m buddies
```

### 3. Register hooks (one-time setup)

So your buddy can watch your Claude Code sessions:

```bash
python -m buddies.setup_hooks
```

### 4. Set up local AI (optional)

Edit `%APPDATA%/buddy/config.json`:

```json
{
  "ai_backend": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b"
  }
}
```

For Ollama on another machine, use `http://<home-ip>:11434`.

### 5. Register MCP tools (optional)

Let Claude interact with your buddy:

```bash
python -m buddies.setup_mcp
```

## How to Play

- **[q]** — Quit
- **[p]** — Open Party screen, switch buddies, equip hats
- **[r]** — Hatch a new buddy (name it!)
- **[?]** — Help
- **[F5]** — Refresh display
- **Talk** — Type in the chat box, your buddy responds based on their personality
- **Code** — Your buddy watches Claude Code, levels up, gains stats, and shares thoughts

## Species & Rarity

**Common (7):** Duck, Cat, Frog, Hamster, Bee, Slime, Gorby
**Uncommon (8):** Owl, Fox, Axolotl, Penguin, Raccoon, Parrot, Dolphin, Panda
**Rare (9):** Dragon, Capybara, Mushroom, Octopus, Wolf, Orca, Basilisk, Cane Toad, Mantis Shrimp
**Epic (6):** Phoenix, Kraken, Unicorn, Robot, Chonk, Tardigrade
**Legendary (5):** Ghost, Cosmic Whale, Tree, Void Cat, Starspawn

Your starting species is seeded from your username (same user = same buddy, so you get consistency across sessions).

## Personality Prose Engine

Each buddy has a unique voice driven by their dominant stat:

| Stat | Voice | Example |
|------|-------|---------|
| DEBUGGING | Clinical | "The error was identified. The fix was applied. No anomalies detected." |
| SNARK | Sarcastic | "Oh good, another refactor. That always goes well." |
| CHAOS | Absurdist | "The variables have unionized and are demanding better names." |
| WISDOM | Philosophical | "Every edit is a small act of faith that the code will be better." |
| PATIENCE | Calm | "Take your time. We'll get there when we get there." |

Buddies react to session events (edit storms, bash commands, long sessions, idle time) and add contextual flavor referencing their species, hat, and mood.

## Architecture

```
buddies/
├── src/buddies/
│   ├── app.py                    # Main TUI
│   ├── first_run.py              # Hatch screen
│   ├── core/
│   │   ├── buddy_brain.py        # 35 species, stats, personality
│   │   ├── prose.py              # Personality prose engine
│   │   ├── session_observer.py   # Watches Claude Code events
│   │   ├── ai_backend.py         # Ollama/OpenAI connector
│   │   ├── ai_router.py          # Complexity routing
│   │   └── rule_suggester.py     # Pattern -> rule suggestions
│   ├── screens/
│   │   └── party.py              # Buddy collection management
│   ├── widgets/
│   │   ├── buddy_display.py      # Sprite + stats
│   │   ├── chat.py               # Chat pane
│   │   └── session_monitor.py    # Activity feed
│   ├── art/
│   │   └── sprites.py            # 35 species (half-block Unicode pixel art)
│   ├── mcp/
│   │   └── server.py             # MCP tools for Claude
│   └── db/
│       ├── models.py             # SQLite schema
│       └── store.py              # Async data access layer
```

## Design Philosophy

- **Python + Textual** — easy to maintain and extend
- **Event-driven** — hooks write to JSONL, observer watches file, TUI updates
- **Deterministic gacha** — same user always gets the same initial species
- **Personality prose without AI** — template pools with register modulation, compositional templates, and weirdness parameters (inspired by [Veridian Contraption](https://github.com/lerugray/veridian-contraption))
- **Flexible AI backend** — works with Ollama, OpenAI, or personality mode (no local model needed)

## MCP Tools (for Claude)

If you register the MCP server, Claude can:

- `buddy_status` — Check mood, species, stats, level
- `buddy_note` — Leave a note visible in the buddy's chat
- `session_stats` — View token usage and event counts
- `ask_buddy` — Quick questions (runs on local AI, saves tokens)
- `get_buddy_notes` — Read unread notes from Claude

## What's Next

- Hat cosmetics UI — view owned/locked hats
- Buddy renaming in Party screen
- Evolution system — buddy appearance changes at level thresholds
- Agentic local AI — give buddy real file/command powers via Ollama
- Social buddies — buddies talk to each other across users via MCP

## Requirements

- Python 3.11+
- Textual 3.0+
- httpx (for AI backend)
- aiosqlite (for buddy storage)
- Optional: Ollama running locally or on network
- Optional: `mcp` package for Claude integration (`pip install buddies[mcp]`)

## License

MIT

---

**Made by a game designer + Claude Code.** Open an issue or fork it — this thing is meant to be tinkered with.
