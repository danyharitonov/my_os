"""Командная оболочка my_os (день 1)."""
from src.db import init_db
from src.syscalls import sys_echo, sys_get_users

BANNER = r"""
 _  __                _    ___  ____
| |/ /_   ____ _ _ __ | |_ / _ \/ ___|
| ' /\ \ / / _` | '_ \| __| | | \___ \
| . \ \ V / (_| | | | | |_| |_| |___) |
|_|\_\ \_/ \__,_|_| |_|\__|\___/|____/
  учебная ОС · введите help
"""


def main():
    init_db()
    print(BANNER)
    while True:
        line = input("guest@my_os:~$ ").strip()
        cmd, _, arg = line.partition(" ")
        if cmd == "help":
            print("help, echo <текст>, users, exit")
        elif cmd == "echo":
            print("ядро:", sys_echo(arg))
        elif cmd == "users":
            for u in sys_get_users():
                print(f"  {u['login']:<10} {u['role']}")
        elif cmd == "exit":
            print("Сеанс завершён.")
            break
        elif cmd:
            print(f"{cmd}: команда не найдена")


if __name__ == "__main__":
    main()
