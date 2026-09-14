"""Командная оболочка my_os (пространство пользователя).

Каждая команда — отдельная функция; таблица COMMANDS связывает имя команды
с обработчиком. Оболочка обращается к ядру только через системные вызовы.
"""
import shlex

from src import config, syscalls as sc

BANNER = rf"""
 _  __                _    ___  ____
| |/ /_   ____ _ _ __ | |_ / _ \/ ___|
| ' /\ \ / / _` | '_ \| __| | | \___ \
| . \ \ V / (_| | | | | |_| |_| |___) |
|_|\_\ \_/ \__,_|_| |_|\__|\___/|____/
  {config.OS_NAME} {config.OS_VERSION} · планировщик Round Robin · введите help
"""


def _fail(what):
    print(f"  отказ: {what}" + (f" ({sc.last_error})" if sc.last_error else ""))


def cmd_help(args):
    for name, (_, text) in COMMANDS.items():
        print(f"  {name:<8} {text}")


def cmd_echo(args):
    print("  ядро:", sc.sys_echo(" ".join(args)))


def cmd_users(args):
    for u in sc.sys_get_users():
        print(f"  {u['login']:<10} {u['role']}")


def cmd_whoami(args):
    print(" ", sc.sys_whoami())


def cmd_login(args):
    login = args[0] if args else input("  логин: ").strip()
    password = input("  пароль: ").strip()
    if sc.sys_login(login, password):
        print(f"  добро пожаловать, {login}")
    else:
        _fail("неверный логин или пароль")


def cmd_logout(args):
    sc.sys_logout()
    print("  сеанс закрыт")


def cmd_create(args):
    path = args[0] if args else input("  путь: ").strip()
    content = " ".join(args[1:]) if len(args) > 1 else input("  содержимое: ")
    fid = sc.sys_create_file(path, content)
    print(f"  создан файл #{fid}") if fid != -1 else _fail("файл не создан")


def cmd_cat(args):
    text = sc.sys_read_file(args[0]) if args else ""
    print(f"  {text}") if text else _fail("нечего показать")


def cmd_rm(args):
    print("  удалён") if args and sc.sys_delete_file(args[0]) else _fail("файл не удалён")


def cmd_ls(args):
    files = sc.sys_list_files(args[0] if args else "/")
    if not files:
        print("  (пусто)" if not sc.last_error else f"  отказ: {sc.last_error}")
    for path in files:
        print(" ", path)


def cmd_run(args):
    if not args:
        return _fail("использование: run <имя> [приоритет 0-3] [память КБ]")
    prio = int(args[1]) if len(args) > 1 else 1
    mem = int(args[2]) if len(args) > 2 else 64
    pid = sc.sys_exec(args[0], prio, mem)
    print(f"  запущен процесс PID={pid}") if pid != -1 else _fail("процесс не запущен")


def cmd_ps(args):
    procs = sc.sys_ps()
    print(f"  {'PID':>4} {'ИМЯ':<12} {'СОСТОЯНИЕ':<10} {'ВЛАДЕЛЕЦ':<9} {'ПРИОР':>5} {'КБ':>5} {'ТАКТЫ':>5}")
    for p in procs:
        print(f"  {p['pid']:>4} {p['name']:<12} {p['state']:<10} {p['owner']:<9} "
              f"{p['priority']:>5} {p['memory_kb']:>5} {p['cpu_ticks']:>5}")
    if not procs:
        print("  (нет процессов)")


def cmd_tick(args):
    trace = sc.sys_tick(int(args[0]) if args else 1)
    print("  CPU:", " → ".join(str(p) if p else "idle" for p in trace))


def cmd_kill(args):
    print("  завершён") if args and sc.sys_kill(int(args[0])) else _fail("процесс не завершён")


def cmd_mem(args):
    total = sc.sys_mem_alloc(int(args[0]), int(args[1]) if len(args) > 1 else None) if args else -1
    print(f"  у процесса теперь {total} КБ") if total != -1 else _fail("память не выделена")


def cmd_logs(args):
    rows = sc.sys_logs(int(args[0]) if args else 10)
    if not rows:
        return _fail("журнал недоступен")
    for r in reversed(rows):
        print(f"  {r['id']:>4} {r['ts']} {r['user']:<8} {r['call_name']:<16} {r['status']}")


def cmd_shutdown(args):
    if sc.sys_shutdown():
        print("  все процессы завершены, система остановлена")
        raise SystemExit(0)
    _fail("выключение не выполнено")


def cmd_exit(args):
    print("  до встречи!")
    raise SystemExit(0)


COMMANDS = {
    "help": (cmd_help, "список команд"),
    "echo": (cmd_echo, "эхо через ядро: echo <текст>"),
    "users": (cmd_users, "пользователи системы"),
    "whoami": (cmd_whoami, "текущий пользователь"),
    "login": (cmd_login, "вход: login [логин]"),
    "logout": (cmd_logout, "выход из сеанса"),
    "create": (cmd_create, "создать файл: create <путь> <текст>"),
    "cat": (cmd_cat, "показать файл: cat <путь>"),
    "rm": (cmd_rm, "удалить файл: rm <путь>"),
    "ls": (cmd_ls, "список файлов: ls [каталог]"),
    "run": (cmd_run, "запуск: run <имя> [приоритет] [КБ]"),
    "ps": (cmd_ps, "таблица процессов"),
    "tick": (cmd_tick, "такты планировщика: tick [N]"),
    "kill": (cmd_kill, "завершить процесс: kill <PID>"),
    "mem": (cmd_mem, "выделить память: mem <КБ> [PID]"),
    "logs": (cmd_logs, "журнал вызовов (admin): logs [N]"),
    "shutdown": (cmd_shutdown, "выключить ОС (admin)"),
    "exit": (cmd_exit, "выйти из оболочки"),
}


def prompt():
    return f"{sc.session_user()}@{config.HOST}:~$ "


def execute(line):
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        return print(f"  ошибка разбора: {exc}")
    if not parts:
        return
    handler = COMMANDS.get(parts[0], (None, ""))[0]
    if handler is None:
        return print(f"  {parts[0]}: команда не найдена (help — список команд)")
    try:
        handler(parts[1:])
    except ValueError:
        print("  ошибка: ожидалось число")


def main():
    print(BANNER)
    while True:
        try:
            line = input(prompt())
        except EOFError:
            print()
            break
        try:
            execute(line)
        except SystemExit:
            break


if __name__ == "__main__":
    main()
