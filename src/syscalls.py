"""Интерфейс системных вызовов my_os (день 1: echo и список пользователей)."""
import json

from src.db import get_connection, init_db


def log_syscall(call_name, args, user, status):
    conn = get_connection()
    conn.execute(
        "INSERT INTO syscalls_log(call_name, args, user, status) VALUES (?, ?, ?, ?)",
        (call_name, json.dumps(args, ensure_ascii=False), user, status),
    )
    conn.commit()


def sys_echo(message, user="guest"):
    log_syscall("sys_echo", {"message": message}, user, "ok")
    return message


def sys_get_users(user="guest"):
    rows = get_connection().execute("SELECT login, role FROM users ORDER BY uid").fetchall()
    log_syscall("sys_get_users", {}, user, "ok")
    return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print(sys_echo("ядро на связи"))
    print(sys_get_users())
