"""Data access layer for Buddy's SQLite database."""

from __future__ import annotations

import aiosqlite
from pathlib import Path

from buddy.db.models import SCHEMA


class BuddyStore:
    """Async SQLite store for all Buddy data."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    @property
    def db(self) -> aiosqlite.Connection:
        assert self._db is not None, "Database not connected"
        return self._db

    # --- Buddy CRUD ---

    async def get_buddy(self) -> dict | None:
        async with self.db.execute("SELECT * FROM buddy WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_buddy(self, species: str, name: str = "Buddy", shiny: bool = False,
                           soul_description: str = "") -> dict:
        await self.db.execute(
            "INSERT INTO buddy (id, species, name, shiny, soul_description) VALUES (1, ?, ?, ?, ?)",
            (species, name, int(shiny), soul_description),
        )
        await self.db.commit()
        return await self.get_buddy()

    async def update_buddy(self, **kwargs) -> dict:
        if not kwargs:
            return await self.get_buddy()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values())
        await self.db.execute(f"UPDATE buddy SET {sets} WHERE id = 1", vals)
        await self.db.commit()
        return await self.get_buddy()

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
