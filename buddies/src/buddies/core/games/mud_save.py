"""MUD Save/Load — persist game state between sessions.

Serializes MudState to JSON in the data directory. On next MUD launch,
the player can continue from where they left off (inventory, quests,
explored rooms, stats, gold).

Items and rooms are rebuilt from the world definition each load —
only mutable state (visited, defeated, picked_up, quest progress) is saved.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime

from buddies.config import get_data_dir

log = logging.getLogger(__name__)


def _save_dir() -> Path:
    """Get the MUD saves directory."""
    d = get_data_dir() / "mud_saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_path(slot: str = "auto") -> Path:
    return _save_dir() / f"{slot}.json"


def list_saves() -> list[dict]:
    """List available save files with metadata."""
    saves = []
    for path in sorted(_save_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            saves.append({
                "slot": path.stem,
                "timestamp": data.get("timestamp", "unknown"),
                "current_room": data.get("current_room", "?"),
                "turns": data.get("stats", {}).get("turns", 0),
                "gold": data.get("gold", 0),
                "quests_completed": data.get("stats", {}).get("quests_completed", 0),
                "rooms_visited": data.get("stats", {}).get("rooms_visited", 0),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return saves


def has_save(slot: str = "auto") -> bool:
    """Check if a save file exists."""
    return _save_path(slot).exists()


def delete_save(slot: str = "auto") -> bool:
    """Delete a save file."""
    path = _save_path(slot)
    if path.exists():
        path.unlink()
        return True
    return False


def save_mud_state(state, slot: str = "auto") -> bool:
    """Serialize MudState to JSON.

    We only save mutable state — the world definition (rooms, items, NPCs)
    is rebuilt from build_starter_*() on load. What we save:
    - Player position (current_room)
    - Inventory (item IDs + gold)
    - Room visited flags + items on ground
    - NPC defeated/talked_to flags
    - Quest statuses + objective progress
    - All stat counters
    - Server status state
    - Bounties claimed
    """
    try:
        data = {
            "version": 1,
            "timestamp": datetime.now().isoformat(),
            "current_room": state.current_room,
            "gold": state.inventory.gold,
            # Inventory: just item IDs (items rebuilt from world def)
            "inventory_items": [item.id for item in state.inventory.items],
            # Room state
            "rooms": {
                rid: {
                    "visited": room.visited,
                    "items": room.items,  # Item IDs on ground
                }
                for rid, room in state.rooms.items()
            },
            # NPC state
            "npcs": {
                nid: {
                    "defeated": npc.defeated,
                    "talked_to": npc.talked_to,
                    "hp": npc.hp,
                }
                for nid, npc in state.npcs.items()
            },
            # Quest state
            "quests": {
                qid: {
                    "status": quest.status.value,
                    "objectives": [
                        {"current": obj.current}
                        for obj in quest.objectives
                    ],
                }
                for qid, quest in state.quests.items()
            },
            # Exit lock state (some get unlocked by keys)
            "unlocked_exits": _get_unlocked_exits(state),
            # Stats
            "stats": {
                "rooms_visited": state.rooms_visited,
                "npcs_talked": state.npcs_talked,
                "npcs_defeated": state.npcs_defeated,
                "items_collected": state.items_collected,
                "quests_completed": state.quests_completed,
                "gold_earned": state.gold_earned,
                "gold_spent": state.gold_spent,
                "gold_gambled": state.gold_gambled,
                "gold_won_gambling": state.gold_won_gambling,
                "tips_given": state.tips_given,
                "bounties_completed": state.bounties_completed,
                "turns": state.turns,
                "notes_left": state.notes_left,
                "notes_rated": state.notes_rated,
                "remote_notes_synced": state.remote_notes_synced,
                "remote_stains_synced": state.remote_stains_synced,
            },
            # Server status
            "server_status": {
                "current_index": state.server_status.current_index,
                "turns_at_status": state.server_status.turns_at_status,
                "incidents_today": state.server_status.incidents_today,
            } if state.server_status else None,
            # Bounties claimed (set → list for JSON)
            "bounties_claimed": list(state._bounties_claimed),
            # Negotiation state (if mid-negotiation)
            "negotiation": {
                "npc_id": state.negotiation.npc_id,
                "stage": state.negotiation.stage,
                "mood": state.negotiation.mood,
                "demands_met": state.negotiation.demands_met,
                "buddy_stat_bonus": state.negotiation.buddy_stat_bonus,
                "roll_history": state.negotiation.roll_history,
            } if state.negotiation else None,
        }

        path = _save_path(slot)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.info("MUD state saved to %s", path)
        return True

    except Exception as e:
        log.error("Failed to save MUD state: %s", e)
        return False


def load_mud_state(state, slot: str = "auto") -> bool:
    """Restore saved state into an existing MudState.

    The MudState should already be created with create_mud_game() so
    all rooms/NPCs/items exist. This function patches the mutable state
    back in from the save file.

    Returns True if load succeeded.
    """
    path = _save_path(slot)
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        version = data.get("version", 0)
        if version < 1:
            log.warning("Unknown save version %s — skipping", version)
            return False

        # Player position
        if data.get("current_room") in state.rooms:
            state.current_room = data["current_room"]

        # Inventory
        state.inventory.gold = data.get("gold", 10)
        saved_item_ids = data.get("inventory_items", [])
        state.inventory.items = []
        for item_id in saved_item_ids:
            if item_id in state.items:
                state.inventory.items.append(state.items[item_id])

        # Room state
        for rid, rdata in data.get("rooms", {}).items():
            if rid in state.rooms:
                state.rooms[rid].visited = rdata.get("visited", False)
                state.rooms[rid].items = rdata.get("items", [])

        # NPC state
        for nid, ndata in data.get("npcs", {}).items():
            if nid in state.npcs:
                state.npcs[nid].defeated = ndata.get("defeated", False)
                state.npcs[nid].talked_to = ndata.get("talked_to", False)
                state.npcs[nid].hp = ndata.get("hp", state.npcs[nid].max_hp)

        # Quest state
        for qid, qdata in data.get("quests", {}).items():
            if qid in state.quests:
                status_str = qdata.get("status", "unknown")
                from buddies.core.games.mud_world import QuestStatus
                try:
                    state.quests[qid].status = QuestStatus(status_str)
                except ValueError:
                    pass
                objectives = qdata.get("objectives", [])
                for i, odata in enumerate(objectives):
                    if i < len(state.quests[qid].objectives):
                        state.quests[qid].objectives[i].current = odata.get("current", 0)

        # Unlock exits that were unlocked
        for exit_key in data.get("unlocked_exits", []):
            room_id, direction = exit_key.rsplit(":", 1)
            if room_id in state.rooms:
                for ex in state.rooms[room_id].exits:
                    if ex.direction == direction:
                        ex.locked = False

        # Stats
        stats = data.get("stats", {})
        state.rooms_visited = stats.get("rooms_visited", 0)
        state.npcs_talked = stats.get("npcs_talked", 0)
        state.npcs_defeated = stats.get("npcs_defeated", 0)
        state.items_collected = stats.get("items_collected", 0)
        state.quests_completed = stats.get("quests_completed", 0)
        state.gold_earned = stats.get("gold_earned", 0)
        state.gold_spent = stats.get("gold_spent", 0)
        state.gold_gambled = stats.get("gold_gambled", 0)
        state.gold_won_gambling = stats.get("gold_won_gambling", 0)
        state.tips_given = stats.get("tips_given", 0)
        state.bounties_completed = stats.get("bounties_completed", 0)
        state.turns = stats.get("turns", 0)
        state.notes_left = stats.get("notes_left", 0)
        state.notes_rated = stats.get("notes_rated", 0)
        state.remote_notes_synced = stats.get("remote_notes_synced", 0)
        state.remote_stains_synced = stats.get("remote_stains_synced", 0)

        # Server status
        ss_data = data.get("server_status")
        if ss_data and state.server_status:
            state.server_status.current_index = ss_data.get("current_index", 0)
            state.server_status.turns_at_status = ss_data.get("turns_at_status", 0)
            state.server_status.incidents_today = ss_data.get("incidents_today", 0)

        # Bounties claimed
        state._bounties_claimed = set(data.get("bounties_claimed", []))

        # Negotiation state (restored if mid-negotiation)
        neg_data = data.get("negotiation")
        if neg_data:
            from buddies.core.games.mud_negotiate import NegotiationState
            state.negotiation = NegotiationState(
                npc_id=neg_data["npc_id"],
                stage=neg_data.get("stage", 0),
                mood=neg_data.get("mood", 50),
                demands_met=neg_data.get("demands_met", 0),
                buddy_stat_bonus=neg_data.get("buddy_stat_bonus", ""),
                roll_history=neg_data.get("roll_history", []),
            )

        log.info("MUD state loaded from %s", path)
        return True

    except Exception as e:
        log.error("Failed to load MUD state: %s", e)
        return False


def _get_unlocked_exits(state) -> list[str]:
    """Collect exits that have been unlocked (were originally locked)."""
    unlocked = []
    # We compare against the default world — any exit that's no longer locked
    # but was originally locked needs to be saved
    from buddies.core.games.mud_world import build_starter_rooms
    default_rooms = build_starter_rooms()
    for rid, room in state.rooms.items():
        if rid not in default_rooms:
            continue
        default_room = default_rooms[rid]
        for ex in room.exits:
            # Find matching default exit
            for dex in default_room.exits:
                if dex.direction == ex.direction and dex.locked and not ex.locked:
                    unlocked.append(f"{rid}:{ex.direction}")
    return unlocked
