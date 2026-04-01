"""Data access layer for Buddy's SQLite database."""

from __future__ import annotations

import aiosqlite
from pathlib import Path

from buddies.db.models import SCHEMA, MIGRATIONS


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
