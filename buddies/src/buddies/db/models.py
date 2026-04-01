"""SQLite schema and database initialization."""

from __future__ import annotations

SCHEMA = """
CREATE TABLE IF NOT EXISTS buddy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    species TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Buddy',
    shiny INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 0,
    hat TEXT DEFAULT NULL,
    hats_owned TEXT NOT NULL DEFAULT '[]',
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

CREATE TABLE IF NOT EXISTS achievements (
    id TEXT PRIMARY KEY,
    unlocked_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS memory_episodic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    session_id TEXT NOT NULL DEFAULT '',
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    importance INTEGER NOT NULL DEFAULT 5,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS memory_semantic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    topic TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'observed',
    confidence REAL NOT NULL DEFAULT 0.5,
    tags TEXT NOT NULL DEFAULT '[]',
    superseded_by INTEGER DEFAULT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS memory_procedural (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    trigger_pattern TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT '',
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT 'observed',
    active INTEGER NOT NULL DEFAULT 1,
    last_applied TEXT DEFAULT NULL
);
"""

# Migration steps for existing databases (idempotent — safe to run on every startup)
MIGRATIONS = [
    "ALTER TABLE buddy ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE buddy ADD COLUMN hat TEXT DEFAULT NULL",
    "ALTER TABLE buddy ADD COLUMN hats_owned TEXT NOT NULL DEFAULT '[]'",
]
