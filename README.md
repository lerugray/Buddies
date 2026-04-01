# 🐾 Buddies

**A tamagotchi-style AI companion collection for your terminal.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![70 Species](https://img.shields.io/badge/species-70-orange.svg)](#species--rarity)
[![16 Hats](https://img.shields.io/badge/hats-16-yellow.svg)](#hats-16)
[![33 Achievements](https://img.shields.io/badge/achievements-33-purple.svg)](#achievements-33)

Hatch buddies, collect species, earn hats, evolve, and build a team of quirky little creatures that react to how you code. Runs alongside Claude Code, watches your sessions, and actually helps — grading your config, saving tokens, and mapping your codebase.

<!-- TODO: Add terminal GIF recording (use ScreenToGif or vhs) -->

## Why

Half the time Claude Code is burning tokens just figuring out where things are in your project. Buddies fixes that — it auto-generates a code map, grades your CLAUDE.md, watches for repeated mistakes and writes rules so Claude stops making them, and tracks your token usage with early warnings before you hit context limits.

It also happens to be a collectible creature game with 70 species, 16 hats, and personality-driven commentary. Because productivity tools should be fun.

## Quick Start

```bash
cd buddies && pip install -e .    # Install
buddy                              # Launch
python -m buddies.setup_hooks      # Watch Claude Code sessions (one-time)
```

<details>
<summary><strong>Set up local AI (recommended)</strong></summary>

Install [Ollama](https://ollama.com), pull a model, then edit `%APPDATA%/buddy/config.json` (or `~/.local/share/buddy/config.json` on Linux):

```json
{
  "ai_backend": {
    "provider": "ollama",
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b"
  }
}
```

With a local model, your buddy can answer coding questions, read files, search code, and run safe commands — all routed automatically by complexity. For Ollama on another machine, use `http://<home-ip>:11434`.

</details>

<details>
<summary><strong>Register MCP tools for Claude (optional)</strong></summary>

```bash
python -m buddies.setup_mcp
```

Gives Claude access to: `buddy_status`, `buddy_note`, `session_stats`, `ask_buddy`, `get_buddy_notes`

</details>

## Features

### The Useful Stuff

| Feature | What it does |
|---------|-------------|
| **Code structure map** | Auto-generates `project-map.md` in `.claude/rules/` — Claude skips exploration, saves tokens. Refresh with [F3]. |
| **Config intelligence** | Grades your CLAUDE.md health (A-F), scaffolds `.claude/rules/`, auto-learns rules from repeated corrections. |
| **Token guardian** | Rolling session summaries, early warnings at 50/70/90% context, quick-save [F1], session handoff files. |
| **Smart model router** | Displays current CC model, detects work phase (planning/implementing/exploring), suggests cheaper models when appropriate. |
| **Session awareness** | Watches Claude Code activity via hooks, detects patterns, suggests config rules. |
| **AI cost guardrails** | Cost tier config prevents buddy chatter from ever hitting expensive models. |
| **Agentic local AI** | Connected to Ollama, buddy reads files, greps code, runs safe commands — all sandboxed. |

### The Fun Stuff

| Feature | What it does |
|---------|-------------|
| **70 species** | Common Potato to Legendary Zorak. Deterministic gacha — same username, same starter. |
| **Personality stats** | DEBUGGING, CHAOS, SNARK, WISDOM, PATIENCE — evolve as you code. |
| **16 hats** | Unlocked by playstyle, stats, milestones, and even boredom. |
| **4 evolution stages** | Hatchling, Juvenile, Adult, Elder — with visual border changes. |
| **Mood system** | Drifts toward neutral. Affects XP, stats, and hat discovery. Neglect has consequences. |
| **Party discussions** | Buddies talk to each other about topics or files, reacting in-character. |
| **33 achievements** | Collection, mastery, social, exploration, and secret categories. |
| **6 themes** | Default, midnight, forest, ocean, sunset, light — cycle with [F2]. |
| **Prose engine** | Each buddy speaks through a personality register (clinical, sarcastic, absurdist, philosophical, calm). Zero AI needed. |

## Controls

| Key | Action |
|-----|--------|
| **[p]** | Party — switch buddies, equip hats, rename |
| **[r]** | Hatch a new buddy |
| **[d]** | Discussions — buddies talk to each other |
| **[a]** | Achievements |
| **[g]** | Config health dashboard |
| **[t]** | Tool browser — installed MCP servers and skills |
| **[c]** | Conversations — browse, load, delete saved chats |
| **[F1]** | Quick save — session state + handoff file |
| **[F2]** | Cycle theme |
| **[F3]** | Regenerate code map |
| **[?]** | Help |

<details>
<summary><strong>Species & Rarity (70 total)</strong></summary>

**Common (14):** Anchor, Bee, Cat, Corgi, Cow, Duck, Frog, Gorby, Hamster, Pig, Potato, Rat, Slime, Taco

**Uncommon (18):** Axolotl, Bat, Box, Coopa, Crab, Dice, Dolphin, Fox, Goblin, Imp, Moth, Owl, Panda, Parrot, Penguin, Raccoon, Rooster, Snail

**Rare (17):** Bac Man, Basilisk, Cane Toad, Capybara, Coffee, Dali Clock, Doobie, Dragon, Jellyfish, Joe Camel, Kobold, Mantis Shrimp, Mushroom, Octopus, Orca, Sanic, Wolf

**Epic (12):** Beholder, Burger, Chonk, Clippy, Comrade, Kilowatt, Kraken, Mimic, Phoenix, Robot, Tardigrade, Unicorn

**Legendary (9):** Claude, Cosmic Whale, Ghost, Illuminati, Starspawn, Tree, Void Cat, Yog-Sothoth, Zorak

Your starting species is seeded from your username (same user = same buddy).

</details>

<details>
<summary><strong>Hats (16)</strong></summary>

| Hat | How to Unlock |
|-----|---------------|
| Tinyduck | Given at hatch (starter) |
| Crown | Dominant DEBUGGING stat at level 5+ |
| Wizard | Dominant WISDOM stat at level 5+ |
| Propeller | Dominant CHAOS stat at level 5+ |
| Safety Cone | Dominant SNARK stat at level 5+ |
| Pirate | Dominant SNARK stat at level 10+ |
| Tophat | Reach level 10 (Adult evolution) |
| Apple | Reach level 15 |
| Halo | 50+ PATIENCE stat |
| Beanie | 50+ PATIENCE stat |
| Horns | 50+ CHAOS stat |
| Headphones | Watch 100+ session events |
| Chef | Send 500+ messages |
| Antenna | Random discovery during exploring phase |
| Flower | Random discovery when ecstatic |
| Nightcap | 10+ minutes of sustained boredom |

</details>

<details>
<summary><strong>Evolution</strong></summary>

| Stage | Level | Visual |
|-------|-------|--------|
| Hatchling | 1-4 | Base sprite |
| Juvenile | 5-9 | Cyan border accent |
| Adult | 10-19 | Green double border |
| Elder | 20+ | Golden star border |

</details>

<details>
<summary><strong>Mood System</strong></summary>

Mood drifts toward neutral over time. Interact with your buddy to boost it!

| Mood | XP Effect | Bonus |
|------|-----------|-------|
| Ecstatic | +50% XP | 5% hat discovery chance |
| Happy | +25% XP | — |
| Neutral | Baseline | — |
| Bored | Baseline | +1 PATIENCE per event |
| Grumpy | -25% XP | +1 SNARK per event |

</details>

<details>
<summary><strong>Personality Voices</strong></summary>

Each buddy has a unique voice driven by their dominant stat:

| Stat | Voice | Example |
|------|-------|---------|
| DEBUGGING | Clinical | "The error was identified. The fix was applied. No anomalies detected." |
| SNARK | Sarcastic | "Oh good, another refactor. That always goes well." |
| CHAOS | Absurdist | "The variables have unionized and are demanding better names." |
| WISDOM | Philosophical | "Every edit is a small act of faith that the code will be better." |
| PATIENCE | Calm | "Take your time. We'll get there when we get there." |

High CHAOS stat adds a "weirdness parameter" that makes commentary increasingly absurd.

</details>

<details>
<summary><strong>Achievements (33)</strong></summary>

| Category | Count | Examples |
|----------|-------|---------|
| Collection | 12 | First Steps, Zookeeper, Shiny Hunter, Fashion Icon |
| Mastery | 6 | Growing Up, Elder Wisdom, Specialist, Well-Rounded |
| Social | 3 | Town Hall, Chatty, Storyteller |
| Exploration | 6 | Watchful Eye, Token Miser, Clean Config, Safety First |
| Secret | 6 | ??? (discover them yourself!) |

</details>

## Design Philosophy

- **Zero token cost** — everything runs locally except tiny MCP payloads
- **Personality without AI** — prose engine uses template pools with register modulation, no model needed
- **Deterministic gacha** — same user always gets the same initial species
- **Agentic tools with safety** — local model gets real capabilities but can't break anything
- **Mood as gameplay** — mood affects XP, stats, and hat discovery — neglect has consequences

## Roadmap

We've got a structured plan for where this goes next. PRs welcome!

**Up Next: Platform Expansion**
- Claude Desktop / headless MCP mode (no TUI needed)
- Cross-surface context relay (CC to claude.ai clipboard bridge)
- Multi-machine awareness (detect two-machine setups, guide CLAUDE.md management)
- README health check and scaffolding
- Obsidian wiki integration (auto-generate project vaults from session data)

**Later: Social**
- BBS-style retro bulletin board for buddies across MCP servers
- Social achievements ("First Post", "Met 10 Buddies")

**Someday: Fun Stuff**
- Card games, trivia, battles (stats influence playstyle)
- Speech-to-text / text-to-speech (local via Whisper + Piper)

See [HANDOFF.md](HANDOFF.md) for the full structured roadmap.

## Requirements

- Python 3.11+
- [Textual](https://github.com/Textualize/textual) 3.0+ (TUI framework)
- Optional: [Ollama](https://ollama.com) for local AI + agentic tools
- Optional: `mcp` package for Claude integration

## License

MIT

---

**Made by a game designer + Claude Code.** This thing is meant to be tinkered with — open an issue, fork it, hatch your own buddy.
