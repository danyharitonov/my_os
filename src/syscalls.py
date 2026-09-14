"""Интерфейс системных вызовов my_os — единственная точка входа в ядро.

Каждый вызов оформлен декоратором @syscall, который:
  * вызывает log_syscall() — запись в таблицу syscalls_log (NFR-S3);
  * перехватывает KernelError и любые исключения, чтобы ядро не падало (NFR-R1);
  * скрывает пароль в журнале (NFR-S4).
"""
import functools
import inspect
import json
import time

from src import config
from src.db import get_connection
from src.kernel import KernelError, get_kernel

last_error = ""          # текст последнего отказа — его показывает оболочка
last_duration_ms = 0.0   # для проверки NFR-P1


def log_syscall(call_name, args, user, status):
    conn = get_connection()
    conn.execute(
        "INSERT INTO syscalls_log(call_name, args, user, status) VALUES (?, ?, ?, ?)",
        (call_name, json.dumps(args, ensure_ascii=False), user, status),
    )
    conn.commit()


def syscall(fail):
    """Декоратор: fail — значение, возвращаемое при отказе ядра."""
    def wrap(func):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def inner(*args, **kwargs):
            global last_error, last_duration_ms
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            shown = {k: ("***" if k == "password" else v) for k, v in bound.arguments.items()}
            user = get_kernel().user
            started = time.perf_counter()
            try:
                result, status, last_error = func(*args, **kwargs), "ok", ""
                if result is fail or result == -1:
                    status = "denied"
            except KernelError as exc:
                result, status, last_error = fail, "denied", str(exc)
            except Exception as exc:  # noqa: BLE001 — ядро не должно падать
                result, status, last_error = fail, "error", f"{type(exc).__name__}: {exc}"
            last_duration_ms = (time.perf_counter() - started) * 1000
            log_syscall(func.__name__, shown, user, status)
            return result
        return inner
    return wrap


def session_user():
    """Имя текущего пользователя для приглашения оболочки.

    Не журналируется (аналог кэшированного getuid в vDSO), иначе каждое
    приглашение засоряло бы syscalls_log.
    """
    return get_kernel().user


@syscall(fail="")
def sys_echo(message):
    return message


@syscall(fail=[])
def sys_get_users():
    return get_kernel().users()


@syscall(fail=False)
def sys_login(login, password):
    return get_kernel().login(login, password)


@syscall(fail=False)
def sys_logout():
    return get_kernel().logout()


@syscall(fail="guest")
def sys_whoami():
    return get_kernel().user


@syscall(fail=-1)
def sys_create_file(path, content=""):
    return get_kernel().create_file(path, content)


@syscall(fail="")
def sys_read_file(path):
    return get_kernel().read_file(path)


@syscall(fail=False)
def sys_delete_file(path):
    return get_kernel().delete_file(path)


@syscall(fail=[])
def sys_list_files(path="/"):
    return get_kernel().list_files(path)


@syscall(fail=-1)
def sys_exec(name, priority=1, memory_kb=64):
    return get_kernel().exec(name, priority, memory_kb)


@syscall(fail=[])
def sys_ps():
    return get_kernel().ps()


@syscall(fail=False)
def sys_kill(pid):
    return get_kernel().kill(pid)


@syscall(fail=-1)
def sys_mem_alloc(size, pid=None):
    return get_kernel().mem_alloc(size, pid)


@syscall(fail=[])
def sys_logs(limit=10):
    return get_kernel().logs(limit)


@syscall(fail=[])
def sys_tick(count=1):
    return get_kernel().tick(count)


@syscall(fail=False)
def sys_shutdown():
    return get_kernel().shutdown()


if __name__ == "__main__":
    print(f"{config.OS_NAME} {config.OS_VERSION}: самопроверка системных вызовов")
    print("sys_login       ->", sys_login("root", "root123"))
    print("sys_whoami      ->", sys_whoami())
    fid = sys_create_file(f"/home/root/selftest-{int(time.time())}.txt", "проверка API")
    print("sys_create_file ->", fid)
    print("sys_ps          ->", sys_ps())
    count = get_connection().execute("SELECT COUNT(*) FROM syscalls_log").fetchone()[0]
    print(f"Записей в syscalls_log: {count}")
