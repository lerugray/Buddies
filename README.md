# 🐾 Buddies — Your Local AI Companion Collection

A tamagotchi-style AI companion that lives in your terminal and watches your Claude Code sessions. Hatch buddies, collect species, earn hats, and build a team of quirky little creatures that react to how you code.

![Buddies TUI — early version](screenshot.jpg)

## What You Get

- **25 species** to collect—from common Frogs to Legendary Void Cats
- **Personality stats** (DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE) that evolve as you code
- **Hats & cosmetics** unlocked by playstyle—crown for debuggers, wizard hat for thinkers, propeller for chaos agents
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
    "model": "qwen3.5:27b"
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

- **[p]** — Open Party screen, switch buddies, equip hats
- **[r]** — Hatch a new buddy (name it!)
- **[+]** — Same as [r]
- **Talk** — Type in the chat box, your buddy responds based on their personality
- **Code** — Your buddy watches Claude Code, levels up, gains stats

## Design Philosophy

- **Python + Textual** — easy to maintain and extend
- **Event-driven** — hooks write to JSONL, observer watches file, TUI updates
- **Deterministic gacha** — same user always gets the same initial species
- **Flexible AI backend** — works with Ollama, OpenAI, or personality mode (no local model needed)

## Architecture

```
buddies/
├── src/buddies/
│   ├── app.py                    # Main TUI
│   ├── core/
│   │   ├── buddy_brain.py        # Species, stats, personality
│   │   ├── session_observer.py   # Watches Claude Code events
│   │   ├── ai_backend.py         # Ollama/OpenAI connector
│   │   └── rule_suggester.py     # Pattern → rule suggestions
│   ├── screens/
│   │   └── party.py              # Buddy collection management
│   ├── widgets/
│   │   ├── buddy_display.py      # Sprite + stats
│   │   ├── chat.py               # Chat pane
│   │   └── session_monitor.py    # Activity feed
│   ├── art/
│   │   ├── sprites.py            # 25 species (half-block Unicode art)
│   │   └── animations.py         # Frame cycling
│   ├── mcp/
│   │   └── server.py             # MCP tools for Claude
│   └── db/
│       └── store.py              # Async SQLite layer
```

## Species & Rarity

**Common:** Frog, Butterfly, Tadpole, Mushroom, Cloud, Bee, Slime  
**Uncommon:** Turtle, Cat, Fish, Penguin, Fox, Raccoon, Parrot  
**Rare:** Dragon, Phoenix, Unicorn, Ghost, Octopus, Wolf  
**Epic:** Robot  
**Legendary:** Tree, Void Cat

Your starting species is seeded from your username (same user = same buddy, so you get consistency across sessions).

## MCP Tools (for Claude)

If you register the MCP server, Claude can:

- `buddy_status` — Check mood, species, stats, level
- `buddy_note` — Leave a note visible in the buddy's chat
- `session_stats` — View token usage and event counts
- `ask_buddy` — Quick questions (runs on local AI, saves tokens)
- `get_buddy_notes` — Read unread notes from Claude

## What's Next

- Input box integration — buddy reacts to your typing
- Hat cosmetics UI — view owned/locked hats
- Buddy renaming in Party screen
- Evolution system — buddy appearance changes at level thresholds
- More animation frames for smoother idle
- Theme customization (dark/light/custom)
- Integration with [claw-code](https://github.com/instructkr/claw-code) for agentic local AI

## Requirements

- Python 3.10+
- Textual 3.0+
- httpx (for AI backend)
- aiosqlite (for buddy storage)
- Optional: Ollama running locally or on network

## License

MIT

---

**Made by a game designer + Claude Code.** Open an issue or fork it—this thing is meant to be tinkered with.
