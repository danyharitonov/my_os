"""Слой хранения my_os: одно соединение с SQLite и схема из четырёх таблиц."""
import hashlib
import sqlite3
import sys
from pathlib import Path

if __package__ in (None, ""):  # запуск как «python src/db.py»
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    uid        INTEGER PRIMARY KEY AUTOINCREMENT,
    login      TEXT UNIQUE NOT NULL,
    pwd_hash   TEXT NOT NULL,
    role       TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS processes (
    pid        INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    state      TEXT NOT NULL DEFAULT 'new',
    owner      TEXT NOT NULL,
    memory_kb  INTEGER NOT NULL DEFAULT 0,
    priority   INTEGER NOT NULL DEFAULT 1,
    cpu_ticks  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS files (
    fid        INTEGER PRIMARY KEY AUTOINCREMENT,
    path       TEXT UNIQUE NOT NULL,
    content    TEXT NOT NULL DEFAULT '',
    owner      TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS syscalls_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    call_name TEXT NOT NULL,
    args      TEXT,
    user      TEXT,
    status    TEXT NOT NULL,
    ts        TEXT DEFAULT (datetime('now', 'localtime'))
);
"""

_conn = None


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_connection():
    """Возвращает единственное на процесс соединение (риск R2 — блокировки)."""
    global _conn
    if _conn is None:
        config.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.DB_FILE)
        _conn.row_factory = sqlite3.Row
    return _conn


def close_connection():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def _migrate(conn):
    """Добавляет столбцы дня 2 в базу, созданную на дне 1."""
    have = {r[1] for r in conn.execute("PRAGMA table_info(processes)")}
    for column in ("priority INTEGER NOT NULL DEFAULT 1", "cpu_ticks INTEGER NOT NULL DEFAULT 0"):
        if column.split()[0] not in have:
            conn.execute(f"ALTER TABLE processes ADD COLUMN {column}")


def init_db():
    """Создаёт таблицы и учётные записи по умолчанию. Повторный вызов безопасен."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate(conn)
    for login, password, role in config.DEFAULT_ACCOUNTS:
        conn.execute(
            "INSERT OR IGNORE INTO users(login, pwd_hash, role) VALUES (?, ?, ?)",
            (login, sha256(password), role),
        )
    conn.commit()
    return conn


if __name__ == "__main__":
    init_db()
    names = [r[0] for r in get_connection().execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    print(f"База {config.DB_FILE} готова. Таблицы: {', '.join(names)}")
