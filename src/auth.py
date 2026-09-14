"""Подсистема пользователей: проверка пароля и правила доступа."""
from src.db import get_connection, sha256


def check_credentials(login, password):
    """Возвращает роль пользователя, если пароль верен, иначе None."""
    row = get_connection().execute(
        "SELECT pwd_hash, role FROM users WHERE login = ?", (login,)).fetchone()
    if row and row["pwd_hash"] == sha256(password):
        return row["role"]
    return None


def list_users():
    rows = get_connection().execute("SELECT uid, login, role FROM users ORDER BY uid")
    return [dict(r) for r in rows]


def may_modify(actor, actor_role, owner):
    """Правило NFR-S2: менять объект может владелец или администратор."""
    return actor_role == "admin" or actor == owner
