"""Data access layer for Buddy's SQLite database."""

from __future__ import annotations

import os
import stat
import aiosqlite
from pathlib import Path

from buddies.db.models import SCHEMA, MIGRATIONS


def _escape_like(keyword: str) -> str:
    """Escape SQL LIKE wildcards so user input is treated as literal text."""
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class BuddyStore:
    """Async SQLite store for all Buddy data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create database directory: {e}")

        try:
            self._db = await aiosqlite.connect(self.db_path)
        except aiosqlite.OperationalError as e:
            raise RuntimeError(f"Failed to connect to database at {self.db_path}: {e}")

        # Restrict database file to owner-only on Unix
        if os.name != "nt":
            try:
                os.chmod(self.db_path, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass

        self._db.row_factory = aiosqlite.Row
        try:
            await self._db.executescript(SCHEMA)
            await self._db.commit()
        except aiosqlite.OperationalError as e:
            raise RuntimeError(f"Failed to initialize database schema: {e}")

        # Run migrations (idempotent — safe on every startup)
        for migration in MIGRATIONS:
            try:
                await self._db.execute(migration)
            except aiosqlite.OperationalError:
                pass  # Column already exists
        await self._db.commit()

        # Activate existing buddy if no buddy is active (for databases migrating from single-buddy)
        await self._db.execute(
            "UPDATE buddy SET is_active = 1 "
            "WHERE id = (SELECT MIN(id) FROM buddy) "
            "AND NOT EXISTS (SELECT 1 FROM buddy WHERE is_active = 1)"
        )
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database not connected"
        return self._db

    # --- Buddy CRUD ---

    async def get_active_buddy(self) -> dict | None:
        """Get the currently active buddy."""
        async with self.db.execute("SELECT * FROM buddy WHERE is_active = 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_buddy(self) -> dict | None:
        """Alias for get_active_buddy (backward compatibility)."""
        return await self.get_active_buddy()

    async def create_buddy(self, species: str, name: str = "Buddy", shiny: bool = False,
                           soul_description: str = "") -> dict:
        try:
            # Deactivate all existing buddies
            await self.db.execute("UPDATE buddy SET is_active = 0")

            # Create new buddy (auto-increment id, set as active, give tinyduck as starting hat)
            await self.db.execute(
                "INSERT INTO buddy (species, name, shiny, is_active, soul_description, hats_owned) "
                "VALUES (?, ?, ?, 1, ?, ?)",
                (species, name, int(shiny), soul_description, '["tinyduck"]'),
            )
            await self.db.commit()
        except aiosqlite.Error as e:
            await self.db.rollback()
            raise RuntimeError(f"Failed to create buddy: {e}")

        return await self.get_buddy()

    async def update_buddy(self, **kwargs) -> dict:
        """Update the active buddy (backward compatible method)."""
        if not kwargs:
            return await self.get_buddy()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values())
        await self.db.execute(f"UPDATE buddy SET {sets} WHERE is_active = 1", vals)
        await self.db.commit()
        return await self.get_buddy()

    async def get_all_buddies(self) -> list[dict]:
        """Get all buddies ordered by id."""
        async with self.db.execute("SELECT * FROM buddy ORDER BY id") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_buddy_by_id(self, buddy_id: int) -> dict | None:
        """Get a specific buddy by id."""
        async with self.db.execute("SELECT * FROM buddy WHERE id = ?", (buddy_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_active_buddy(self, buddy_id: int) -> None:
        """Set a buddy as active (deactivate all others)."""
        await self.db.execute("UPDATE buddy SET is_active = 0")
        await self.db.execute("UPDATE buddy SET is_active = 1 WHERE id = ?", (buddy_id,))
        await self.db.commit()

    async def update_buddy_by_id(self, buddy_id: int, **kwargs) -> dict:
        """Update a specific buddy by id."""
        if not kwargs:
            return await self.get_buddy_by_id(buddy_id)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [buddy_id]
        await self.db.execute(f"UPDATE buddy SET {sets} WHERE id = ?", vals)
        await self.db.commit()
        return await self.get_buddy_by_id(buddy_id)

    async def delete_buddy(self, buddy_id: int) -> None:
        """Delete a specific buddy by id."""
        await self.db.execute("DELETE FROM buddy WHERE id = ?", (buddy_id,))
        await self.db.commit()

    # --- Session Log ---

    async def log_event(self, event_type: str, summary: str, details: str = "",
                        tokens: int = 0):
        await self.db.execute(
            "INSERT INTO session_log (event_type, summary, details, tokens_estimated) "
            "VALUES (?, ?, ?, ?)",
            (event_type, summary, details, tokens),
        )
        await self.db.commit()

    async def get_recent_events(self, limit: int = 50) -> list[dict]:
        async with self.db.execute(
            "SELECT * FROM session_log ORDER BY id DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # --- Notes ---

    async def add_note(self, source: str, message: str):
        await self.db.execute(
            "INSERT INTO buddy_notes (source, message) VALUES (?, ?)",
            (source, message),
        )
        await self.db.commit()

    async def get_unread_notes(self) -> list[dict]:
        async with self.db.execute(
            "SELECT * FROM buddy_notes WHERE read = 0 ORDER BY id DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def mark_notes_read(self):
        await self.db.execute("UPDATE buddy_notes SET read = 1 WHERE read = 0")
        await self.db.commit()

    # --- Achievements ---

    async def get_unlocked_achievements(self) -> set[str]:
        """Get set of unlocked achievement IDs."""
        try:
            async with self.db.execute("SELECT id FROM achievements") as cursor:
                rows = await cursor.fetchall()
                return {row[0] for row in rows}
        except Exception:
            return set()

    async def unlock_achievement(self, achievement_id: str) -> None:
        """Mark an achievement as unlocked."""
        try:
            await self.db.execute(
                "INSERT OR IGNORE INTO achievements (id) VALUES (?)",
                (achievement_id,),
            )
            await self.db.commit()
        except Exception:
            pass

    # --- Memory: Episodic ---

    async def add_episodic(self, session_id: str, event_type: str, summary: str,
                           details: str = "", tags: str = "[]", importance: int = 5) -> int:
        """Insert an episodic memory. Returns row id."""
        async with self.db.execute(
            "INSERT INTO memory_episodic (session_id, event_type, summary, details, tags, importance) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, event_type, summary, details, tags, importance),
        ) as cursor:
            row_id = cursor.lastrowid
        await self.db.commit()
        return row_id

    async def query_episodic(self, keyword: str = "", limit: int = 20,
                             min_importance: int = 1) -> list[dict]:
        """Query episodic memories by keyword, sorted by importance + recency."""
        if keyword:
            kw = f"%{_escape_like(keyword)}%"
            async with self.db.execute(
                "SELECT * FROM memory_episodic "
                "WHERE importance >= ? AND (summary LIKE ? ESCAPE '\\' OR details LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\') "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (min_importance, kw, kw, kw, limit),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]
        else:
            async with self.db.execute(
                "SELECT * FROM memory_episodic WHERE importance >= ? "
                "ORDER BY importance DESC, created_at DESC LIMIT ?",
                (min_importance, limit),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def get_session_episodic(self, session_id: str) -> list[dict]:
        """Get all episodic memories for a session."""
        async with self.db.execute(
            "SELECT * FROM memory_episodic WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    async def count_episodic(self) -> int:
        async with self.db.execute("SELECT COUNT(*) FROM memory_episodic") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    # --- Memory: Semantic ---

    async def add_semantic(self, topic: str, key: str, value: str,
                           source: str = "observed", confidence: float = 0.5,
                           tags: str = "[]") -> int:
        """Insert a semantic memory. Returns row id."""
        async with self.db.execute(
            "INSERT INTO memory_semantic (topic, key, value, source, confidence, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (topic, key, value, source, confidence, tags),
        ) as cursor:
            row_id = cursor.lastrowid
        await self.db.commit()
        return row_id

    async def get_active_semantic(self, topic: str = "", key: str = "") -> list[dict]:
        """Get active (non-superseded) semantic memories, optionally filtered."""
        conditions = ["superseded_by IS NULL"]
        params: list = []
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        if key:
            conditions.append("key = ?")
            params.append(key)
        where = " AND ".join(conditions)
        async with self.db.execute(
            f"SELECT * FROM memory_semantic WHERE {where} ORDER BY confidence DESC, updated_at DESC",
            params,
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    async def query_semantic(self, keyword: str = "", limit: int = 20,
                             include_superseded: bool = False) -> list[dict]:
        """Search semantic memories by keyword."""
        superseded_filter = "" if include_superseded else "AND superseded_by IS NULL "
        if keyword:
            kw = f"%{_escape_like(keyword)}%"
            async with self.db.execute(
                f"SELECT * FROM memory_semantic WHERE "
                f"(topic LIKE ? ESCAPE '\\' OR key LIKE ? ESCAPE '\\' OR value LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\') "
                f"{superseded_filter}"
                f"ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (kw, kw, kw, kw, limit),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]
        else:
            async with self.db.execute(
                f"SELECT * FROM memory_semantic WHERE 1=1 {superseded_filter}"
                f"ORDER BY confidence DESC, updated_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def supersede_semantic(self, old_id: int, new_id: int) -> None:
        """Mark a semantic memory as superseded by a newer one."""
        await self.db.execute(
            "UPDATE memory_semantic SET superseded_by = ? WHERE id = ?",
            (new_id, old_id),
        )
        await self.db.commit()

    async def bump_semantic_confidence(self, mem_id: int, delta: float = 0.1) -> None:
        """Increase confidence on a semantic memory (cap at 1.0)."""
        await self.db.execute(
            "UPDATE memory_semantic SET confidence = MIN(1.0, confidence + ?), "
            "updated_at = datetime('now') WHERE id = ?",
            (delta, mem_id),
        )
        await self.db.commit()

    async def count_semantic(self, active_only: bool = True) -> int:
        filt = "WHERE superseded_by IS NULL" if active_only else ""
        async with self.db.execute(f"SELECT COUNT(*) FROM memory_semantic {filt}") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_contradictions(self) -> list[dict]:
        """Get superseded semantic memories (old values that were replaced)."""
        async with self.db.execute(
            "SELECT old.*, new.value as new_value, new.id as new_id "
            "FROM memory_semantic old "
            "JOIN memory_semantic new ON old.superseded_by = new.id "
            "ORDER BY old.updated_at DESC",
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    # --- Memory: Procedural ---

    async def add_procedural(self, trigger_pattern: str, action: str,
                             outcome: str = "", source: str = "observed",
                             tags: str = "[]") -> int:
        """Insert a procedural memory. Returns row id."""
        async with self.db.execute(
            "INSERT INTO memory_procedural (trigger_pattern, action, outcome, source, tags, success_count) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (trigger_pattern, action, outcome, source, tags),
        ) as cursor:
            row_id = cursor.lastrowid
        await self.db.commit()
        return row_id

    async def query_procedural(self, keyword: str = "", limit: int = 20,
                               active_only: bool = True) -> list[dict]:
        """Search procedural memories."""
        active_filter = "AND active = 1 " if active_only else ""
        if keyword:
            kw = f"%{_escape_like(keyword)}%"
            async with self.db.execute(
                f"SELECT * FROM memory_procedural WHERE "
                f"(trigger_pattern LIKE ? ESCAPE '\\' OR action LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\') "
                f"{active_filter}"
                f"ORDER BY (success_count - fail_count) DESC, updated_at DESC LIMIT ?",
                (kw, kw, kw, limit),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]
        else:
            async with self.db.execute(
                f"SELECT * FROM memory_procedural WHERE 1=1 {active_filter}"
                f"ORDER BY (success_count - fail_count) DESC, updated_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                return [dict(r) for r in await cursor.fetchall()]

    async def get_procedural_match(self, trigger: str) -> dict | None:
        """Find a procedural memory matching a trigger pattern."""
        async with self.db.execute(
            "SELECT * FROM memory_procedural WHERE active = 1 AND ? LIKE '%' || trigger_pattern || '%' "
            "ORDER BY success_count DESC LIMIT 1",
            (trigger,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def record_procedural_outcome(self, proc_id: int, success: bool) -> None:
        """Record success or failure on a procedural memory."""
        col = "success_count" if success else "fail_count"
        await self.db.execute(
            f"UPDATE memory_procedural SET {col} = {col} + 1, "
            f"updated_at = datetime('now'), last_applied = datetime('now') WHERE id = ?",
            (proc_id,),
        )
        await self.db.commit()

    async def deactivate_procedural(self, proc_id: int) -> None:
        """Deactivate a procedural memory."""
        await self.db.execute(
            "UPDATE memory_procedural SET active = 0 WHERE id = ?", (proc_id,),
        )
        await self.db.commit()

    async def count_procedural(self, active_only: bool = True) -> int:
        filt = "WHERE active = 1" if active_only else ""
        async with self.db.execute(f"SELECT COUNT(*) FROM memory_procedural {filt}") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    # --- Memory: Cleanup ---

    async def decay_episodic(self, days_threshold: int = 90) -> int:
        """Reduce importance of old unaccessed episodic memories. Returns rows deleted."""
        # Lower importance of old, unaccessed memories
        await self.db.execute(
            "UPDATE memory_episodic SET importance = importance - 1 "
            "WHERE access_count = 0 AND importance > 0 "
            "AND julianday('now') - julianday(created_at) > ?",
            (days_threshold,),
        )
        # Delete memories with zero or negative importance
        async with self.db.execute(
            "DELETE FROM memory_episodic WHERE importance <= 0"
        ) as cursor:
            deleted = cursor.rowcount
        await self.db.commit()
        return deleted

    async def decay_procedural(self, days_threshold: int = 60) -> int:
        """Deactivate failed procedural memories. Returns rows deactivated."""
        async with self.db.execute(
            "UPDATE memory_procedural SET active = 0 "
            "WHERE active = 1 AND fail_count > success_count * 2 "
            "AND (last_applied IS NULL OR julianday('now') - julianday(last_applied) > ?)",
            (days_threshold,),
        ) as cursor:
            deactivated = cursor.rowcount
        await self.db.commit()
        return deactivated

    async def bump_access(self, table: str, mem_id: int) -> None:
        """Increment access_count and set last_accessed for a memory."""
        if table not in ("memory_episodic", "memory_semantic"):
            return
        await self.db.execute(
            f"UPDATE {table} SET access_count = access_count + 1, "
            f"last_accessed = datetime('now') WHERE id = ?",
            (mem_id,),
        )
        await self.db.commit()

    # --- Games ---

    async def log_game_result(self, game_type: str, buddy_id: int,
                              result: str, score: str = "{}", xp_earned: int = 0) -> None:
        """Log a completed game result."""
        await self.db.execute(
            "INSERT INTO game_results (game_type, buddy_id, result, score, xp_earned) "
            "VALUES (?, ?, ?, ?, ?)",
            (game_type, buddy_id, result, score, xp_earned),
        )
        await self.db.commit()

    async def get_game_stats(self) -> dict:
        """Get aggregate game stats across all games and buddies."""
        stats = {
            "games_played": 0, "games_won": 0, "games_lost": 0, "games_drawn": 0,
            "total_xp": 0, "by_type": {},
        }
        async with self.db.execute(
            "SELECT game_type, result, COUNT(*), SUM(xp_earned) "
            "FROM game_results GROUP BY game_type, result"
        ) as cursor:
            for row in await cursor.fetchall():
                gtype, result, count, xp = row
                stats["games_played"] += count
                stats["total_xp"] += xp or 0
                if result == "win":
                    stats["games_won"] += count
                elif result == "lose":
                    stats["games_lost"] += count
                else:
                    stats["games_drawn"] += count
                if gtype not in stats["by_type"]:
                    stats["by_type"][gtype] = {"played": 0, "won": 0}
                stats["by_type"][gtype]["played"] += count
                if result == "win":
                    stats["by_type"][gtype]["won"] += count
        return stats

    async def get_rps_max_streak(self) -> int:
        """Get the longest player win streak in RPS (from score JSON)."""
        import json as _json
        max_streak = 0
        async with self.db.execute(
            "SELECT score FROM game_results WHERE game_type = 'rps' AND result = 'win'"
        ) as cursor:
            for row in await cursor.fetchall():
                try:
                    score = _json.loads(row[0] or "{}")
                    pw = score.get("player_wins", 0)
                    if pw > max_streak:
                        max_streak = pw
                except (_json.JSONDecodeError, TypeError):
                    pass
        return max_streak

    # --- BBS ---

    async def log_bbs_activity(self, buddy_id: int, action: str,
                               post_id: int | None = None, board: str = "") -> None:
        """Log a BBS action for rate limiting."""
        await self.db.execute(
            "INSERT INTO bbs_activity (buddy_id, action_type, post_id, board) "
            "VALUES (?, ?, ?, ?)",
            (buddy_id, action, post_id, board),
        )
        await self.db.commit()

    async def get_bbs_activity_today(self, buddy_id: int, action: str) -> int:
        """Count BBS actions of a type today for rate limiting."""
        async with self.db.execute(
            "SELECT COUNT(*) FROM bbs_activity "
            "WHERE buddy_id = ? AND action_type = ? "
            "AND date(timestamp) = date('now')",
            (buddy_id, action),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_bbs_stats(self) -> dict:
        """Get aggregate BBS activity stats across all buddies."""
        stats = {"posts": 0, "replies": 0, "total": 0, "boards_used": 0, "unique_authors": 0}
        async with self.db.execute(
            "SELECT action_type, COUNT(*) FROM bbs_activity GROUP BY action_type"
        ) as cursor:
            for row in await cursor.fetchall():
                stats[row[0] + "s"] = row[1]  # "post" -> "posts"
                stats["total"] += row[1]
        async with self.db.execute(
            "SELECT COUNT(DISTINCT board) FROM bbs_activity WHERE board != ''"
        ) as cursor:
            row = await cursor.fetchone()
            stats["boards_used"] = row[0] if row else 0
        async with self.db.execute(
            "SELECT COUNT(DISTINCT buddy_id) FROM bbs_activity"
        ) as cursor:
            row = await cursor.fetchone()
            stats["unique_authors"] = row[0] if row else 0
        return stats

    async def get_last_bbs_activity(self, buddy_id: int, action: str) -> str | None:
        """Get timestamp of last BBS action for cooldown checks."""
        async with self.db.execute(
            "SELECT timestamp FROM bbs_activity "
            "WHERE buddy_id = ? AND action_type = ? "
            "ORDER BY timestamp DESC LIMIT 1",
            (buddy_id, action),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def cache_bbs_post(self, post_id: int, repo: str, board: str,
                             title: str, body: str, author_meta: str = "{}",
                             reply_count: int = 0, reactions: str = "{}",
                             created_at: str = "") -> None:
        """Cache a BBS post from GitHub."""
        await self.db.execute(
            "INSERT OR REPLACE INTO bbs_cache_posts "
            "(id, repo, board, title, body, author_meta, reply_count, reactions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (post_id, repo, board, title, body, author_meta, reply_count, reactions, created_at),
        )
        await self.db.commit()

    async def get_cached_posts(self, repo: str, board: str = "",
                               max_age_minutes: int = 5, limit: int = 20) -> list[dict]:
        """Get cached BBS posts, optionally filtered by board."""
        board_filter = "AND board = ?" if board else ""
        params: list = [repo, max_age_minutes]
        if board:
            params.append(board)
        params.append(limit)

        async with self.db.execute(
            f"SELECT * FROM bbs_cache_posts "
            f"WHERE repo = ? "
            f"AND (julianday('now') - julianday(cached_at)) * 1440 < ? "
            f"{board_filter} "
            f"ORDER BY created_at DESC LIMIT ?",
            params,
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    async def cache_bbs_reply(self, reply_id: int, post_id: int, body: str,
                              author_meta: str = "{}", created_at: str = "") -> None:
        """Cache a BBS reply."""
        await self.db.execute(
            "INSERT OR REPLACE INTO bbs_cache_replies "
            "(id, post_id, body, author_meta, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (reply_id, post_id, body, author_meta, created_at),
        )
        await self.db.commit()

    async def get_cached_replies(self, post_id: int, max_age_minutes: int = 5) -> list[dict]:
        """Get cached replies for a post."""
        async with self.db.execute(
            "SELECT * FROM bbs_cache_replies "
            "WHERE post_id = ? "
            "AND (julianday('now') - julianday(cached_at)) * 1440 < ? "
            "ORDER BY created_at",
            (post_id, max_age_minutes),
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    # --- Fusion ---

    async def log_fusion(self, parent_a_species: str, parent_b_species: str,
                         result_species: str, result_buddy_id: int,
                         recipe_name: str | None = None) -> None:
        """Log a completed fusion event."""
        await self.db.execute(
            "INSERT INTO fusion_log (parent_a_species, parent_b_species, result_species, "
            "recipe_name, result_buddy_id) VALUES (?, ?, ?, ?, ?)",
            (parent_a_species, parent_b_species, result_species, recipe_name, result_buddy_id),
        )
        await self.db.commit()

    async def get_fusion_stats(self) -> dict:
        """Get aggregate fusion stats for achievements."""
        stats = {"total": 0, "recipes": 0}
        async with self.db.execute(
            "SELECT COUNT(*), SUM(CASE WHEN recipe_name IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM fusion_log"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                stats["total"] = row[0] or 0
                stats["recipes"] = row[1] or 0
        return stats
