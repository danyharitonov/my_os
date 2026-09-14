"""Подсистема памяти: учёт килобайт, выделенных процессам, и общий лимит."""
from src import config
from src.db import get_connection

LIVE = "state != 'terminated'"


def used_kb():
    row = get_connection().execute(f"SELECT COALESCE(SUM(memory_kb), 0) FROM processes WHERE {LIVE}")
    return row.fetchone()[0]


def free_kb():
    return config.MEMORY_LIMIT_KB - used_kb()


def can_allocate(size_kb):
    return 0 < size_kb <= free_kb()


def grow(pid, size_kb):
    """Добавляет память процессу. Возвращает новый объём или -1 (NFR-R2)."""
    if not can_allocate(size_kb):
        return -1
    conn = get_connection()
    conn.execute("UPDATE processes SET memory_kb = memory_kb + ? WHERE pid = ?", (size_kb, pid))
    conn.commit()
    return conn.execute("SELECT memory_kb FROM processes WHERE pid = ?", (pid,)).fetchone()[0]


def release(pid):
    conn = get_connection()
    conn.execute("UPDATE processes SET memory_kb = 0 WHERE pid = ?", (pid,))
    conn.commit()
