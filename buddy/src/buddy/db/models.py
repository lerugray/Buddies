"""SQLite schema and database initialization."""

from __future__ import annotations

SCHEMA = """
CREATE TABLE IF NOT EXISTS buddy (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    species TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Buddy',
    shiny INTEGER NOT NULL DEFAULT 0,
    stat_debugging INTEGER NOT NULL DEFAULT 10,
    stat_patience INTEGER NOT NULL DEFAULT 10,
    stat_chaos INTEGER NOT NULL DEFAULT 10,
    stat_wisdom INTEGER NOT NULL DEFAULT 10,
    stat_snark INTEGER NOT NULL DEFAULT 10,
    xp INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 1,
    mood TEXT NOT NULL DEFAULT 'neutral',
    mood_value INTEGER NOT NULL DEFAULT 50,
    hatched_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen TEXT NOT NULL DEFAULT (datetime('now')),
    soul_description TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS session_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    tokens_estimated INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rule_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    rule_type TEXT NOT NULL,
    rule_content TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    times_suggested INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS buddy_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    read INTEGER NOT NULL DEFAULT 0
);
"""
