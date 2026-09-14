"""Файловая система my_os поверх таблицы files."""
from src.db import get_connection


def create(path, content, owner):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO files(path, content, owner) VALUES (?, ?, ?)", (path, content, owner))
    conn.commit()
    return cur.lastrowid


def stat(path):
    row = get_connection().execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
    return dict(row) if row else None


def read(path):
    info = stat(path)
    return info["content"] if info else None


def remove(path):
    conn = get_connection()
    cur = conn.execute("DELETE FROM files WHERE path = ?", (path,))
    conn.commit()
    return cur.rowcount == 1


def listdir(prefix):
    prefix = prefix.rstrip("/") + "/" if prefix not in ("", "/") else "/"
    rows = get_connection().execute(
        "SELECT path FROM files WHERE path LIKE ? ORDER BY path", (prefix + "%",))
    return [r["path"] for r in rows]
