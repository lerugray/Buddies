# BUDDIES Refactor — Multi-Buddy Collection System

## Context
The current single-buddy model (enforced by `CHECK (id = 1)` in the DB) limits the fun. Hatching a new buddy destroys the old one. The user wants a collection system where you keep every buddy you hatch, name them, and switch between them. Also renaming the project from "Buddy" to "BUDDIES" and making keybindings visible.

## Implementation Steps

### Step 1: Schema + Store (foundation)

**`buddy/src/buddy/db/models.py`**
- Remove `CHECK (id = 1)` from buddy table
- Change to `id INTEGER PRIMARY KEY AUTOINCREMENT`
- Add `is_active INTEGER NOT NULL DEFAULT 0` column
- Add migration SQL for existing single-buddy databases

**`buddy/src/buddy/db/store.py`**
- Add `_migrate_if_needed()` — detects old schema, migrates existing buddy to new schema with `is_active = 1`
- Replace `get_buddy()` → `get_active_buddy()`
- Add `get_all_buddies()`, `get_buddy_by_id()`, `get_buddy_count()`
- `create_buddy()` — remove hardcoded `id = 1`, add `set_active` param that deactivates others first
- `update_buddy(buddy_id, **kwargs)` — takes explicit buddy_id
- Add `set_active_buddy(buddy_id)`, `rename_buddy(buddy_id, name)`

### Step 2: BuddyState gets an ID

**`buddy/src/buddy/core/buddy_brain.py`**
- Add `buddy_id: int` to `BuddyState` dataclass
- Update `from_db()` to read `data["id"]`

### Step 3: App multi-buddy wiring

**`buddy/src/buddy/app.py`**
- `on_mount()` → use `get_active_buddy()`
- Hatch flow → creates new buddy in collection (no delete)
- `on_unmount()` → save with explicit `buddy_id`
- XP/stat saves → pass `buddy_id`
- Change `r` binding from "Rehatch" to "Hatch New"
- Add `p` binding for "Party" screen
- Add `_on_party_result()` to handle buddy switching/renaming

**`buddy/src/buddy/mcp/server.py`**
- Change `get_buddy()` → `get_active_buddy()` (must happen with Step 1)

### Step 4: Naming on hatch

**`buddy/src/buddy/first_run.py`**
- Add name Input field, pre-filled with species name
- Dismiss result becomes 4-tuple: `(species, shiny, seed, custom_name)`
- Title → "HATCH A NEW BUDDY"

### Step 5: Party screen (new file)

**`buddy/src/buddy/party.py`** (new)
- `PartyScreen(Screen)` with `OptionList` showing all buddies
- Each entry: emoji, name, level, rarity color, "[ACTIVE]" tag
- Keybindings: `enter` switch active, `n` rename, `h` hatch new, `escape` close
- Dismisses with action type so app knows what changed
- CRITICAL: no methods named `_render*` or `_compose*`

### Step 6: Footer replaces StatusBar

**`buddy/src/buddy/app.py`**
- Replace `StatusBar` with Textual's built-in `Footer` widget
- Remove all `query_one("#status-bar")` calls
- Use `self.notify()` for alerts instead of `status.set_alert()`

**Delete `buddy/src/buddy/widgets/status_bar.py`**

### Step 7: Rename to BUDDIES

- `pyproject.toml` → `name = "buddies"`
- `app.py` → `TITLE = "BUDDIES — Your AI Companions"`
- `mcp/server.py` → `FastMCP("Buddies")`
- `chat.py` → use buddy's actual name in chat messages
- `HANDOFF.md` → update everything

### Step 8: More species

**`buddy/src/buddy/core/buddy_brain.py`** — add ~9 new species:
- Common: bee, slime
- Uncommon: raccoon, parrot
- Rare: octopus, wolf
- Epic: robot, tree
- Legendary: void_cat

**`buddy/src/buddy/art/sprites.py`** — add colored half-block sprites for each

## Verification

After each step:
1. **Step 1**: Run import check + DB migration test on existing `.db` file
2. **Step 3**: Launch TUI, hatch a second buddy, confirm first still exists in DB
3. **Step 4**: Hatch with custom name, confirm it displays
4. **Step 5**: Press `p`, see all buddies, switch, rename
5. **Step 6**: Confirm footer shows all keybindings automatically
6. **Step 7**: Confirm title and MCP server name updated
7. **Step 8**: Random roll, confirm new species can appear
8. **Final**: Full sanity check (all imports, no Textual method collisions, sprite render check, DB flow)

## Pitfalls to Avoid
- **No `_render` method names** — shadows Textual internal
- **No fixed-width containers** — user has a small terminal
- **MCP server must update alongside Step 1** — `get_buddy()` gets removed
- **Keep data dir as `buddy`** — renaming would lose existing DB
- **Migration must be idempotent** — fresh installs skip it, reruns skip it
